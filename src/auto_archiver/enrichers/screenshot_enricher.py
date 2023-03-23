from loguru import logger
import time, uuid, os
from selenium.common.exceptions import TimeoutException

from . import Enricher
from ..utils import Webdriver, UrlUtil
from ..core import Media, Metadata, ArchivingContext

class ScreenshotEnricher(Enricher):
    name = "screenshot_enricher"

    @staticmethod
    def configs() -> dict:
        return {
            "width": {"default": 1280, "help": "width of the screenshots"},
            "height": {"default": 720, "help": "height of the screenshots"},
            "timeout": {"default": 60, "help": "timeout for taking the screenshot"},
            "sleep_before_screenshot": {"default": 4, "help": "seconds to wait for the pages to load before taking screenshot"}
        }

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        if UrlUtil.is_auth_wall(url):
            logger.debug(f"[SKIP] SCREENSHOT since url is behind AUTH WALL: {url=}")
            return

        logger.debug(f"Enriching screenshot for {url=}")
        with Webdriver(self.width, self.height, self.timeout, 'facebook.com' in url) as driver:
            try:
                driver.get(url)
                time.sleep(int(self.sleep_before_screenshot))
                screenshot_file = os.path.join(ArchivingContext.get_tmp_dir(), f"screenshot_{str(uuid.uuid4())[0:8]}.png")
                driver.save_screenshot(screenshot_file)
                to_enrich.add_media(Media(filename=screenshot_file), id="screenshot")
            except TimeoutException:
                logger.info("TimeoutException loading page for screenshot")
            except Exception as e:
                logger.error(f"Got error while loading webdriver for screenshot enricher: {e}")
