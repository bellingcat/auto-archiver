import re, json, mimetypes, os

from loguru import logger
from vk_url_scraper import VkScraper, DateTimeEncoder

from storages import Storage
from .base_archiver import Archiver, ArchiveResult
from configs import Config


class VkArchiver(Archiver):
    """"
    VK videos are handled by YTDownloader, this archiver gets posts text and images.
    Currently only works for /wall posts
    """
    name = "vk"
    wall_pattern = re.compile(r"(wall.{0,1}\d+_\d+)")
    photo_pattern = re.compile(r"(photo.{0,1}\d+_\d+)")

    def __init__(self, storage: Storage, config: Config): 
        super().__init__(storage, config)
        if config.vk_config != None:
            self.vks = VkScraper(config.vk_config.username, config.vk_config.password)

    def download(self, url, check_if_exists=False):
        if not hasattr(self, "vks") or self.vks is None:
            logger.debug("VK archiver was not supplied with credentials.")
            return False

        key = self.get_html_key(url)
        # if check_if_exists and self.storage.exists(key):
        #     screenshot = self.get_screenshot(url)
        #     cdn_url = self.storage.get_cdn_url(key)
        #     return ArchiveResult(status="already archived", cdn_url=cdn_url, screenshot=screenshot)

        results = self.vks.scrape(url)  # some urls can contain multiple wall/photo/... parts and all will be fetched
        if len(results) == 0:
            return False

        def dump_payload(p): return json.dumps(p, ensure_ascii=False, indent=4, cls=DateTimeEncoder)
        textual_output = ""
        title, datetime = results[0]["text"], results[0]["datetime"]
        urls_found = []
        for res in results:
            textual_output += f"id: {res['id']}<br>time utc: {res['datetime']}<br>text: {res['text']}<br>payload: {dump_payload(res['payload'])}<br><hr/><br>"
            title = res["text"] if len(title) == 0 else title
            datetime = res["datetime"] if not datetime else datetime
            for attachments in res["attachments"].values():
                urls_found.extend(attachments)

        # we don't call generate_media_page which downloads urls because it cannot download vk video urls
        thumbnail, thumbnail_index = None, None
        uploaded_media = []
        filenames = self.vks.download_media(results, Storage.TMP_FOLDER)
        for filename in filenames:
            key = self.get_key(filename)
            self.storage.upload(filename, key)
            hash = self.get_hash(filename)
            cdn_url = self.storage.get_cdn_url(key)
            try:
                _type = mimetypes.guess_type(filename)[0].split("/")[0]
                if _type == "image" and thumbnail is None:
                    thumbnail = cdn_url
                if _type == "video" and (thumbnail is None or thumbnail_index is None):
                    thumbnail, thumbnail_index = self.get_thumbnails(filename, key)
            except Exception as e:
                logger.warning(f"failed to get thumb for {filename=} with {e=}")
            uploaded_media.append({'cdn_url': cdn_url, 'key': key, 'hash': hash})

        page_cdn, page_hash, thumbnail = self.generate_media_page_html(url, uploaded_media, textual_output, thumbnail=thumbnail)
        # # if multiple wall/photos/videos are present the screenshot will only grab the 1st
        screenshot = self.get_screenshot(url)
        wacz = self.get_wacz(url)
        return ArchiveResult(status="success", cdn_url=page_cdn, screenshot=screenshot, hash=page_hash, thumbnail=thumbnail, thumbnail_index=thumbnail_index, timestamp=datetime, title=title, wacz=wacz)
