from loguru import logger
import time, os
import base64

from selenium.common.exceptions import TimeoutException


from auto_archiver.base_processors import Enricher
from auto_archiver.utils import Webdriver, UrlUtil, random_str
from auto_archiver.core import Media, Metadata, ArchivingContext

class ScreenshotEnricher(Enricher):
    name = "screenshot_enricher"

    def __init__(self, config: dict) -> None:
        super().__init__(config)

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()

        if UrlUtil.is_auth_wall(url):
            logger.debug(f"[SKIP] SCREENSHOT since url is behind AUTH WALL: {url=}")
            return

        logger.debug(f"Enriching screenshot for {url=}")
        with Webdriver(self.width, self.height, self.timeout, 'facebook.com' in url, http_proxy=self.http_proxy, print_options=self.print_options) as driver:
            try:
                driver.get(url)
                time.sleep(int(self.sleep_before_screenshot))
                screenshot_file = os.path.join(ArchivingContext.get_tmp_dir(), f"screenshot_{random_str(8)}.png")
                driver.save_screenshot(screenshot_file)
                to_enrich.add_media(Media(filename=screenshot_file), id="screenshot")
                if self.save_to_pdf:
                    pdf_file = os.path.join(ArchivingContext.get_tmp_dir(), f"pdf_{random_str(8)}.pdf")
                    pdf = driver.print_page(driver.print_options)
                    with open(pdf_file, "wb") as f:
                        f.write(base64.b64decode(pdf))
                    to_enrich.add_media(Media(filename=pdf_file), id="pdf")
            except TimeoutException:
                logger.info("TimeoutException loading page for screenshot")
            except Exception as e:
                logger.error(f"Got error while loading webdriver for screenshot enricher: {e}")
