import re, json

from loguru import logger
from utils.misc import DateTimeEncoder
from vk_url_scraper import VkScraper

from storages import Storage
from .base_archiver import Archiver, ArchiveResult
from configs import VkConfig


class VkArchiver(Archiver):
    """"
    VK videos are handled by YTDownloader, this archiver gets posts text and images.
    Currently only works for /wall posts
    """
    name = "vk"
    wall_pattern = re.compile(r"(wall.{0,1}\d+_\d+)")
    photo_pattern = re.compile(r"(photo.{0,1}\d+_\d+)")

    def __init__(self, storage: Storage, driver, config: VkConfig):
        super().__init__(storage, driver)
        if config != None:
            self.vks = VkScraper(config.username, config.password)

    def download(self, url, check_if_exists=False):
        if not hasattr(self, "vks") or self.vks is None:
            logger.debug("VK archiver was not supplied with credentials.")
            return False

        key = self.get_html_key(url)
        if check_if_exists and self.storage.exists(key):
            screenshot = self.get_screenshot(url)
            cdn_url = self.storage.get_cdn_url(key)
            return ArchiveResult(status="already archived", cdn_url=cdn_url, screenshot=screenshot)

        results = self.vks.scrape(url)  # some urls can contain multiple wall/photo/... parts and all will be fetched
        if len(results) == 0:
            return False


        dump_payload = lambda p : json.dumps(p, ensure_ascii=False, indent=4, cls=DateTimeEncoder)
        textual_output = ""
        title, time = results[0]["text"], results[0]["datetime"]
        urls_found = []
        for res in results:
            textual_output+= f"id: {res['id']}<br>time utc: {res['datetime']}<br>text: {res['text']}<br>payload: {dump_payload(res['payload'])}<br><hr/><br>"
            title = res["text"] if len(title) == 0 else title
            time = res["datetime"] if not time else time
            for attachments in res["attachments"].values():
                urls_found.extend(attachments)

        page_cdn, page_hash, thumbnail = self.generate_media_page(urls_found, url, textual_output)
        # if multiple wall/photos/videos are present the screenshot will only grab the 1st
        screenshot = self.get_screenshot(url)
        return ArchiveResult(status="success", cdn_url=page_cdn, screenshot=screenshot, hash=page_hash, thumbnail=thumbnail, timestamp=time, title=title)
