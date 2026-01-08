import base64
import math
import os
import sys
import traceback
from urllib.parse import urljoin
import glob
import importlib.util

from auto_archiver.utils.custom_logger import logger
import selenium
from seleniumbase import SB

from auto_archiver.core import Extractor, Enricher, Metadata, Media
from auto_archiver.modules.antibot_extractor_enricher.dropin import Dropin
from auto_archiver.modules.antibot_extractor_enricher.dropins.default import DefaultDropin
from auto_archiver.utils.misc import random_str
from auto_archiver.utils.url import is_relevant_url


class AntibotExtractorEnricher(Extractor, Enricher):
    def setup(self) -> None:
        self.agent = "cool"
        if "linux" in sys.platform or "win32" in sys.platform:
            self.agent = None  # Use the default UserAgent

        # parse configuration options
        if self.max_download_images == "inf":
            self.max_download_images = math.inf
        else:
            self.max_download_images = int(self.max_download_images)

        if self.max_download_videos == "inf":
            self.max_download_videos = math.inf
        else:
            self.max_download_videos = int(self.max_download_videos)

        self._prepare_user_data_dir()

        self.dropins = self.load_dropins()

    def load_dropins(self):
        dropins = []

        # TODO: add user-configurable drop-ins via config like generic_extractor
        dropins_dir = os.path.join(os.path.dirname(__file__), "dropins")
        for file_path in glob.glob(os.path.join(dropins_dir, "*.py")):
            if os.path.basename(file_path).startswith("_"):
                continue  # skip __init__.py or private modules
            module_name = f"auto_archiver.modules.antibot_extractor_enricher.dropins.{os.path.splitext(os.path.basename(file_path))[0]}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for attr in dir(module):
                obj = getattr(module, attr)
                if getattr(obj, "__module__", None) != module.__name__:
                    continue  # Skip imported modules/classes/functions
                if isinstance(obj, type) and issubclass(obj, Dropin):
                    dropins.append(obj)
        logger.debug(f"Loaded drop-in classes: {', '.join([d.__name__ for d in dropins])}")
        return dropins

    def sanitize_url(self, url: str) -> str:
        for dropin in self.dropins:
            if dropin.suitable(url):
                return dropin.sanitize_url(url)
        return url

    def download(self, item: Metadata) -> Metadata:
        result = Metadata()
        result.merge(item)
        if self.enrich(result):
            result.status = "antibot"
            return result

    def _prepare_user_data_dir(self):
        if self.user_data_dir:
            in_docker = os.environ.get("RUNNING_IN_DOCKER")
            if in_docker:
                self.user_data_dir = self.user_data_dir.rstrip(os.path.sep) + "_docker"
            os.makedirs(self.user_data_dir, exist_ok=True)

    def enrich(self, to_enrich: Metadata, custom_data_dir: bool = True) -> bool:
        if to_enrich.get_media_by_id("html_source_code"):
            logger.info("Antibot has already been executed, skipping.")
            return True
        using_user_data_dir = self.user_data_dir if custom_data_dir else None
        url = to_enrich.get_url()

        try:
            with SB(uc=True, agent=self.agent, headed=None, user_data_dir=using_user_data_dir, proxy=self.proxy) as sb:
                logger.info(f"Selenium browser is up with agent {self.agent}, opening url...")
                sb.uc_open_with_reconnect(url, 4)

                logger.debug("Handling CAPTCHAs for...")
                sb.uc_gui_handle_cf()
                sb.uc_gui_click_rc()  # NB: using handle instead of click breaks some sites like reddit, for now we separate here but can have dropins deciding this in the future

                dropin = self._get_suitable_dropin(url, sb)
                if not dropin.open_page(url):
                    # TODO: could we detect deleted videos?
                    logger.warning("Failed to open drop-in page")
                    return False

                if self.detect_auth_wall and (dropin.hit_auth_wall() and self._hit_auth_wall(sb)):
                    logger.warning("Skipping since auth wall or CAPTCHA was detected")
                    return False

                sb.wait_for_ready_state_complete()
                sb.sleep(1)  # margin for the page to load completely

                to_enrich.set_title(sb.get_title())
                self._enrich_html_source_code(sb, to_enrich)

                self._enrich_full_page_screenshot(sb, to_enrich)
                if self.save_to_pdf:
                    self._enrich_full_page_pdf(sb, to_enrich)

                downloaded_images, downloaded_videos = dropin.add_extra_media(to_enrich)

                self._enrich_download_media(
                    sb,
                    to_enrich,
                    js_css_selector=dropin.js_for_image_css_selectors(),
                    max_media=self.max_download_images - downloaded_images,
                )
                self._enrich_download_media(
                    sb,
                    to_enrich,
                    js_css_selector=dropin.js_for_video_css_selectors(),
                    max_media=self.max_download_videos - downloaded_videos,
                )
                logger.info("Completed")

            return to_enrich
        except selenium.common.exceptions.SessionNotCreatedException as e:
            if custom_data_dir:  # the retry logic only works once
                logger.error(
                    f"Session not created error: {e}. Please remove the user_data_dir {self.user_data_dir} and try again, will retry without user data dir though."
                )
                return self.enrich(to_enrich, custom_data_dir=False)
            raise e  # re-raise
        except Exception as e:
            logger.error(f"Runtime error: {e}: {traceback.format_exc()}")
            return False

    def _get_suitable_dropin(self, url: str, sb: SB):
        """
        Returns a suitable drop-in for the given URL.
        This method checks if the URL is suitable for any of the registered drop-ins.
        """
        for dropin in self.dropins:
            if dropin.suitable(url):
                logger.debug(f"Using drop-in {dropin.__name__}")
                return dropin(sb, self)

        return DefaultDropin(sb, self)

    def _hit_auth_wall(self, sb: SB) -> bool:
        """
        Tries to detect if the currently loaded page is an auth/login wall.
        Returns True if login is likely required.
        """
        # TODO: improve this detection logic, currently it is very basic and may not cover all cases

        # Common URL patterns
        current_url = sb.get_current_url().lower()
        if any(kw in current_url for kw in ["login", "signin", "signup", "register", "captcha"]):
            return True

        # Common visible text markers
        login_keywords = [
            "sign up or log in",
            "log in to continue",
            "sign in to continue",
            "login required",
            "please log in",
            "please sign up",
            "please sign in",
            "login to access",
            "sign up to access",
            "register to access",
            "captcha verification",
        ]
        for word in login_keywords + [w.capitalize() for w in login_keywords]:
            if sb.is_text_visible(word):
                return True

        # Common title markers
        title = sb.get_title().lower()
        if any(
            kw in title
            for kw in [
                "just a moment...",
                "tiktok - make your day",
                "um momento...",
                "log in",
                "sign in",
                "sign up",
                "register",
                "captcha",
                "verification required",
                "access denied",
            ]
        ):
            return True

        # Common form fields
        elements = [
            "input[type='password']",
            "input[type='email']",
            "input[type='username']",
            "input[type='phone']",
            "input[name='username']",
            "input[name='email']",
            "input[name='password']",
            "input[name='login']",
        ]
        if any(sb.is_element_visible(el) for el in elements):
            return True

        return False

    @logger.catch
    def _enrich_html_source_code(self, sb: SB, to_enrich: Metadata):
        """
        Enriches the HTML source code of the Metadata object.
        This method is called by the enrich method.
        """
        source = sb.get_page_source()

        html_filename = os.path.join(self.tmp_dir, f"source{random_str(6)}.html")
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(source)

        to_enrich.add_media(Media(filename=html_filename), id="html_source_code")

    @logger.catch
    def _enrich_full_page_screenshot(self, sb: SB, to_enrich: Metadata):
        """
        Enriches the full page screenshot of the Metadata object.
        This method is called by the enrich method.
        """
        start_size = sb.get_window_size()
        w, h = start_size["width"], start_size["height"]

        x = max(sb.execute_script("return document.documentElement.scrollWidth"), w)
        y = min(max(sb.execute_script("return document.documentElement.scrollHeight"), h), 25_000)
        logger.debug(f"Setting window size to {x}x{y} for full page screenshot.")
        sb.set_window_size(x, y)

        screen_filename = os.path.join(self.tmp_dir, f"screenshot{random_str(6)}.png")
        sb.save_screenshot(screen_filename)

        to_enrich.add_media(Media(filename=screen_filename), id="screenshot")

    @logger.catch
    def _enrich_full_page_pdf(self, sb: SB, to_enrich: Metadata):
        """
        Enriches the full page PDF of the Metadata object.
        This method is called by the enrich method.
        """
        result = sb.driver.execute_cdp_cmd("Page.printToPDF", {"printBackground": True, "landscape": False})

        pdf_data = base64.b64decode(result["data"])

        pdf_filename = os.path.join(self.tmp_dir, f"pdf{random_str(6)}.pdf")
        with open(pdf_filename, "wb") as f:
            f.write(pdf_data)

        to_enrich.add_media(Media(filename=pdf_filename), id="pdf")

    @logger.catch
    def _enrich_download_media(self, sb: SB, to_enrich: Metadata, js_css_selector: str, max_media: int):
        """
        Downloads media from the page and adds them to the Metadata object.
        This method is called by the enrich method.
        """
        if max_media == 0:
            return
        url = to_enrich.get_url()
        all_urls = set()
        logger.debug(f"Extracting media for {js_css_selector=}")

        try:
            sources = sb.execute_script(js_css_selector)
        except selenium.common.exceptions.JavascriptException as e:
            logger.error(f"Error executing JavaScript selector {js_css_selector}: {e}")
            return

        # js_for_css_selectors
        for src in sources:
            if len(all_urls) >= max_media:
                logger.debug(f"Reached max download limit of {max_media} images/videos.")
                break
            if not is_relevant_url(src):
                continue
            full_src = urljoin(url, src)
            if full_src not in all_urls:
                filename, full_src = self.download_from_url(full_src, try_best_quality=True)
                if not filename:
                    continue
                all_urls.add(full_src)
                to_enrich.add_media(Media(filename=filename, properties={"url": full_src}))
