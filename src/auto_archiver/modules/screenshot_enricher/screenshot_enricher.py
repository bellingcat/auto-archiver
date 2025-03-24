from loguru import logger
import time
import os
import base64

from selenium.common.exceptions import TimeoutException


from auto_archiver.core import Enricher
from auto_archiver.utils import Webdriver, url as UrlUtil, random_str
from auto_archiver.core import Media, Metadata


class ScreenshotEnricher(Enricher):
    def __init__(self, webdriver_factory=None):
        super().__init__()
        self.webdriver_factory = webdriver_factory or Webdriver

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()

        logger.debug(f"Enriching screenshot for {url=}")
        auth = self.auth_for_site(url)

        # screenshot enricher only supports cookie-type auth (selenium)
        has_valid_auth = auth and (auth.get("cookies") or auth.get("cookies_jar") or auth.get("cookie"))

        if UrlUtil.is_auth_wall(url) and not has_valid_auth:
            logger.warning(f"[SKIP] SCREENSHOT since url is behind AUTH WALL and no login details provided: {url=}")
            if any(auth.get(key) for key in ["username", "password", "api_key", "api_secret"]):
                logger.warning(
                    f"Screenshot enricher only supports cookie-type authentication, you have provided {auth.keys()} which are not supported.\
                               Consider adding 'cookie', 'cookies_file' or 'cookies_from_browser' to your auth for this site."
                )
            return

        with self.webdriver_factory(
            self.width,
            self.height,
            self.timeout,
            facebook_accept_cookies="facebook.com" in url,
            http_proxy=self.http_proxy,
            print_options=self.print_options,
            auth=auth,
        ) as driver:
            try:
                driver.get(url)
                time.sleep(int(self.sleep_before_screenshot))
                screenshot_file = os.path.join(self.tmp_dir, f"screenshot_{random_str(8)}.png")
                driver.save_screenshot(screenshot_file)
                to_enrich.add_media(Media(filename=screenshot_file), id="screenshot")
                if self.save_to_pdf:
                    pdf_file = os.path.join(self.tmp_dir, f"pdf_{random_str(8)}.pdf")
                    pdf = driver.print_page(driver.print_options)
                    with open(pdf_file, "wb") as f:
                        f.write(base64.b64decode(pdf))
                    to_enrich.add_media(Media(filename=pdf_file), id="pdf")
            except TimeoutException:
                logger.info("TimeoutException loading page for screenshot")
            except Exception as e:
                logger.error(f"Got error while loading webdriver for screenshot enricher: {e}")
