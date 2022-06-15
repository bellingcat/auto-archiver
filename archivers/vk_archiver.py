import re, json

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
    onclick_pattern = re.compile(r"({.*})")

    def __init__(self, storage: Storage, driver, config: VkConfig):
        super().__init__(storage, driver)
        if config != None:
            self.vk_session = vk_api.VkApi(config.username, config.password)
            self.vk_session.auth(token_only=True)

    def download(self, url, check_if_exists=False):
        # detect URLs that this archiver can handle
        has_wall = self.wall_pattern.search(url)
        if has_wall:
            wall_url = f'https://vk.com/{has_wall[0]}'
            logger.info(f"found valid wall id from {url=} : {wall_url=}")
            return self.archive_wall(wall_url, check_if_exists)
        return False

    def archive_wall(self, wall_url, check_if_exists):
        res = self.vk_session.http.get(wall_url).text
        soup = BeautifulSoup(res, "html.parser")
        image_urls = []
        time = None
        try:
            rel_date = soup.find("a", class_="post_link").find("span", class_="rel_date")
            t = rel_date.get_text()
            if "time" in rel_date.attrs:
                t = rel_date["time"]
            elif "abs_time" in rel_date.attrs:
                t = rel_date["abs_time"]
            time = dateparser.parse(t, settings={"RETURN_AS_TIMEZONE_AWARE": True, "TO_TIMEZONE": "UTC"})
        except Exception as e:
            logger.warning(f"could not fetch time from post: {e}")

        post = soup.find("div", class_="wall_text")
        post_text = post.find(class_="wall_post_text").get_text()
        for anchor in post.find_all("a", attrs={"aria-label": "photo"}):
            if img_url := self.get_image_from_anchor(anchor):
                image_urls.append(img_url)

        page_cdn, page_hash, thumbnail = self.generate_media_page(image_urls, wall_url, post_text, requester=self.vk_session.http)
        screenshot = self.get_screenshot(wall_url)
        return ArchiveResult(status="success", cdn_url=page_cdn, screenshot=screenshot, hash=page_hash, thumbnail=thumbnail, timestamp=time)

    def get_image_from_anchor(self, anchor):
        try:
            # get anchor.onlick text, retrieve the JSON value there
            # retrieve "temp"."z" which contains the image with more quality
            temp_json = json.loads(self.onclick_pattern.search(anchor["onclick"])[0])["temp"]
            for quality in ["z", "y", "x"]:  # decreasing quality
                if quality in temp_json:
                    return temp_json[quality]
        except Exception as e:
            logger.warning(f"failed to get image from vk wall anchor: {e}")
        return False
