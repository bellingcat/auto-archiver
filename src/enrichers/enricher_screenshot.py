from . import Enricher
from metadata import Metadata
from loguru import logger


class ScreenshotEnricher(Enricher):
    name = "screenshot"

    @staticmethod
    def configs() -> dict:
        return {
            "width": {"default": 1280, "help": "width of the screenshots"},
            "height": {"default": 720, "help": "height of the screenshots"},
        }

    def enrich(self, item: Metadata) -> Metadata:
        url = self.get_url(item)
        print("enrich")
        # driver = config.webdriver
        # with driver as Webdriver(): # TODO: make a util
        #     #TODO: take screenshot
        #     pass

        # logger.debug(f"getting screenshot for {url=}")
        # key = self._get_key_from_url(url, ".png", append_datetime=True)
        # filename = os.path.join(Storage.TMP_FOLDER, key)

        # # Accept cookies popup dismiss for ytdlp video
        # if 'facebook.com' in url:
        #     try:
        #         logger.debug(f'Trying fb click accept cookie popup for {url}')
        #         self.driver.get("http://www.facebook.com")
        #         foo = self.driver.find_element(By.XPATH, "//button[@data-cookiebanner='accept_only_essential_button']")
        #         foo.click()
        #         logger.debug(f'fb click worked')
        #         # linux server needs a sleep otherwise facebook cookie won't have worked and we'll get a popup on next page
        #         time.sleep(2)
        #     except:
        #         logger.warning(f'Failed on fb accept cookies for url {url}')

        # try:
        #     self.driver.get(url)
        #     time.sleep(6)
        # except TimeoutException:
        #     logger.info("TimeoutException loading page for screenshot")

        # self.driver.save_screenshot(filename)
        # self.storage.upload(filename, key, extra_args={'ACL': 'public-read', 'ContentType': 'image/png'})

        # cdn_url = self.storage.get_cdn_url(key)
        # self.add_to_media(cdn_url, key)

        # return cdn_url
