import base64
import math
import mimetypes
import os
import sys
import traceback
from urllib.parse import urljoin

from loguru import logger
from seleniumbase import SB

from auto_archiver.core import Extractor, Enricher, Metadata, Media
from auto_archiver.utils.misc import random_str


class AntibotExtractorEnricher(Extractor, Enricher):
    def setup(self) -> None:
        self.agent = "cool"
        if "linux" in sys.platform or "win32" in sys.platform:
            self.agent = None  # Use the default UserAgent

        # parse configuration options
        self.exclude_media_mimetypes = set(
            [mimetypes.guess_type(f"file{m}")[0] for m in self.exclude_media_extensions.split(",")]
        ) - {None}

        if self.max_download_images == "inf":
            self.max_download_images = math.inf
        else:
            self.max_download_images = int(self.max_download_images)

        if self.max_download_videos == "inf":
            self.max_download_videos = math.inf
        else:
            self.max_download_videos = int(self.max_download_videos)

    def download(self, item: Metadata) -> Metadata:
        result = Metadata()
        result.merge(item)
        if self.enrich(result):
            result.status = "antibot"
            return result

    def enrich(self, to_enrich: Metadata) -> bool:
        url = to_enrich.get_url()
        # TODO: implement cookies auth = self.auth_for_site(url)
        url_sample = url[:75]
        try:
            with SB(uc=True, agent=self.agent, headed=None, proxy=self.proxy) as sb:
                logger.info(f"ANTIBOT selenium browser is up with agent {self.agent}, opening {url_sample}...")
                sb.uc_open_with_reconnect(url, 4)

                logger.debug(f"ANTIBOT handling CAPTCHAs for {url_sample}...")

                # TODO: implement other Captcha handling
                sb.uc_gui_handle_captcha()  # handles Cloudflare Turnstile captcha if detected

                # time.sleep(1)  # wait for the page to load
                if self._hit_auth_wall(sb):
                    logger.warning(f"ANTIBOT SKIP since auth wall or CAPTCHA was detected for {url_sample}")
                    return False
                logger.debug(f"ANTIBOT no auth wall detected for {url_sample}...")

                to_enrich.set_title(sb.get_title())
                self._enrich_html_source_code(sb, to_enrich)
                self._enrich_full_page_screenshot(sb, to_enrich)
                if self.save_to_pdf:
                    self._enrich_full_page_pdf(sb, to_enrich)

                self._enrich_download_media(sb, to_enrich, css_selector="img", max_media=self.max_download_images)
                self._enrich_download_media(
                    sb, to_enrich, css_selector="video, source", max_media=self.max_download_videos
                )

                logger.success(f"ANTIBOT completed for {url_sample}")

            return to_enrich
        except Exception as e:
            logger.error(f"ANTIBOT runtime error: {e}: {traceback.format_exc()}")
            return False

    def _hit_auth_wall(self, sb: SB) -> bool:
        """
        Tries to detect if the currently loaded page is an auth/login wall.
        Returns True if login is likely required.
        """
        # TODO: improve this detection logic, currently it is very basic and may not cover all cases

        # Common URL patterns
        url = sb.get_current_url().lower()
        if any(kw in url for kw in ["login", "signin", "signup", "register", "captcha"]):
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
        x = sb.execute_script("return document.documentElement.scrollWidth")
        y = min(sb.execute_script("return document.documentElement.scrollHeight"), 25_000)
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
    def _enrich_download_media(self, sb: SB, to_enrich: Metadata, css_selector: str, max_media: int):
        """
        Downloads media from the page and adds them to the Metadata object.
        This method is called by the enrich method.
        """
        if max_media == 0:
            return
        logger.debug(
            f"Downloading media from {to_enrich.get_url()} with selector '{css_selector}' up to {max_media} items."
        )
        url = to_enrich.get_url()
        all_urls = set()
        media_elements = sb.find_elements(css_selector)
        for media in media_elements:
            if len(all_urls) >= max_media:
                logger.debug(f"Reached max download limit of {max_media} images/videos.")
                break
            if src := media.get_attribute("src"):
                mimerype = mimetypes.guess_type(src)[0]
                if mimerype in self.exclude_media_mimetypes:
                    continue
                full_src = urljoin(url, src)
                if full_src not in all_urls and (filename := self.download_from_url(full_src)):
                    all_urls.add(full_src)
                    to_enrich.add_media(Media(filename=filename, properties={"url": full_src}))
