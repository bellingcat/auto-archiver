from utils import Webdriver
from . import Enricher
from metadata import Metadata
from loguru import logger
from selenium.common.exceptions import TimeoutException
import time


class ScreenshotEnricher(Enricher):
    name = "screenshot"

    @staticmethod
    def configs() -> dict:
        return {
            "width": {"default": 1280, "help": "width of the screenshots"},
            "height": {"default": 720, "help": "height of the screenshots"},
            "timeout": {"default": 60, "help": "timeout for taking the screenshot"}
        }

    def enrich(self, item: Metadata) -> Metadata:
        url = self.get_url(item)
        print(f"enriching {url=}")
        with Webdriver(self.width, self.height, self.timeout, 'facebook.com' in url) as driver:  # TODO: make a util
            try:
                driver.get(url)
                time.sleep(2)
            except TimeoutException:
                logger.info("TimeoutException loading page for screenshot")

        #TODO: return saved object
            driver.save_screenshot("TODO-HASH_OR_UUID.png")
        return None
