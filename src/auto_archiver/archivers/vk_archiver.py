from loguru import logger
from vk_url_scraper import VkScraper

from ..utils.misc import dump_payload
from . import Archiver
from ..core import Metadata, Media, ArchivingContext


class VkArchiver(Archiver):
    """"
    VK videos are handled by YTDownloader, this archiver gets posts text and images.
    Currently only works for /wall posts
    """
    name = "vk_archiver"

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

    def is_rearchivable(self, url: str) -> bool:
        # VK content is static
        return False

    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()

        if "vk.com" not in item.netloc: return False

        # some urls can contain multiple wall/photo/... parts and all will be fetched
        vk_scrapes = self.vks.scrape(url)
        if not len(vk_scrapes): return False
        logger.debug(f"VK: got {len(vk_scrapes)} scraped instances")

        result = Metadata()
        for scrape in vk_scrapes:
            if not result.get_title():
                result.set_title(scrape["text"])
            if not result.get_timestamp():
                result.set_timestamp(scrape["datetime"])

        result.set_content(dump_payload(vk_scrapes))

        filenames = self.vks.download_media(vk_scrapes, ArchivingContext.get_tmp_dir())
        for filename in filenames:
            result.add_media(Media(filename))

        return result.success("vk")
