import re, json, requests

import vk_api, dateparser
from bs4 import BeautifulSoup
from loguru import logger

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
    onclick_pattern = re.compile(r"({.*})")

    def __init__(self, storage: Storage, driver, config: VkConfig):
        super().__init__(storage, driver)
        if config != None:
            self.vk_session = vk_api.VkApi(config.username, config.password)
            self.vk_session.auth(token_only=True)

    def download(self, url, check_if_exists=False):
        # detect URLs that this archiver can handle
        _id, method = None, None
        if has_wall := self.wall_pattern.search(url):
            _id = has_wall[0]
            method = self.archive_wall
        elif has_photo := self.photo_pattern.search(url):
            _id = has_photo[0]
            method = self.archive_photo
        else: return False

        logger.info(f"found valid {_id=} from {url=}")
        proper_url = f'https://vk.com/{_id}'

        # if check if exists will not download again
        key = self.get_html_key(proper_url)
        if check_if_exists and self.storage.exists(key):
            screenshot = self.get_screenshot(proper_url)
            cdn_url = self.storage.get_cdn_url(key)
            return ArchiveResult(status="already archived", cdn_url=cdn_url, screenshot=screenshot)

        return method(proper_url, _id)

    def archive_photo(self, photo_url, photo_id):
        headers = {"access_token": self.vk_session.token["access_token"], "photos": photo_id.replace("photo", ""), "extended": "1", "v": self.vk_session.api_version}
        req = requests.get("https://api.vk.com/method/photos.getById", headers)
        res = req.json()["response"][0]
        title = res["text"][:200] # more on the page
        img_url = res["orig_photo"]["url"]
        time = dateparser.parse(str(res["date"]), settings={"RETURN_AS_TIMEZONE_AWARE": True, "TO_TIMEZONE": "UTC"})

        page_cdn, page_hash, thumbnail = self.generate_media_page([img_url], photo_url, res)
        screenshot = self.get_screenshot(photo_url)
        return ArchiveResult(status="success", cdn_url=page_cdn, screenshot=screenshot, hash=page_hash, thumbnail=thumbnail, timestamp=time, title=title)

    def archive_wall(self, wall_url, wall_id):
        headers = {"access_token": self.vk_session.token["access_token"], "posts": wall_id.replace("wall", ""), "extended": "1", "copy_history_depth": "2", "v": self.vk_session.api_version}
        req = requests.get("https://api.vk.com/method/wall.getById", headers)
        res = req.json()["response"]
        wall = res["items"][0]
        img_urls = [p[p["type"]]["sizes"][-1]["url"] for p in wall["attachments"]] if "attachments" in wall else []
        title = wall["text"][:200] # more on the page
        time = dateparser.parse(str(wall["date"]), settings={"RETURN_AS_TIMEZONE_AWARE": True, "TO_TIMEZONE": "UTC"})

        page_cdn, page_hash, thumbnail = self.generate_media_page(img_urls, wall_url, res)
        screenshot = self.get_screenshot(wall_url)
        return ArchiveResult(status="success", cdn_url=page_cdn, screenshot=screenshot, hash=page_hash, thumbnail=thumbnail, timestamp=time, title=title)

