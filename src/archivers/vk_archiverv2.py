import re, json, mimetypes, os

from loguru import logger
from vk_url_scraper import VkScraper, DateTimeEncoder

from metadata import Metadata
from media import Media
from utils.misc import dump_payload
from .archiver import Archiverv2


class VkArchiver(Archiverv2):
    """"
    VK videos are handled by YTDownloader, this archiver gets posts text and images.
    Currently only works for /wall posts
    """
    name = "vk_archiver"
    wall_pattern = re.compile(r"(wall.{0,1}\d+_\d+)")
    photo_pattern = re.compile(r"(photo.{0,1}\d+_\d+)")

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.assert_valid_string("username")
        self.assert_valid_string("password")
        self.vks = VkScraper(self.username, self.password, session_file=self.session_file)

    @staticmethod
    def configs() -> dict:
        return {
            "username": {"default": None, "help": "valid VKontakte username"},
            "password": {"default": None, "help": "valid VKontakte password"},
            "session_file": {"default": "secrets/vk_config.v2.json", "help": "valid VKontakte password"},
        }

    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()

        if "vk.com" not in item.netloc: return False

        # some urls can contain multiple wall/photo/... parts and all will be fetched
        vk_scrapes = self.vks.scrape(url)
        if not len(vk_scrapes): return False

        result = Metadata()
        for scrape in vk_scrapes:
            if not result.get_title():
                result.set_title(scrape["text"])
            if not result.get_timestamp():
                result.set_timestamp(scrape["datetime"])

        result.set_content(dump_payload(vk_scrapes))

        textual_output = ""
        title, datetime = vk_scrapes[0]["text"], vk_scrapes[0]["datetime"]
        urls_found = []
        for scrape in vk_scrapes:
            textual_output += f"id: {scrape['id']}<br>time utc: {scrape['datetime']}<br>text: {scrape['text']}<br>payload: {dump_payload(scrape['payload'])}<br><hr/><br>"
            title = scrape["text"] if len(title) == 0 else title
            datetime = scrape["datetime"] if not datetime else datetime
            for attachments in scrape["attachments"].values():
                urls_found.extend(attachments)

        filenames = self.vks.download_media(vk_scrapes, item.get_tmp_dir())
        for filename in filenames:
            result.add_media(Media(filename))

        return result.success("vk")
