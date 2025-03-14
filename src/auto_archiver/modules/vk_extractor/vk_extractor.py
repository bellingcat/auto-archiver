from loguru import logger
from vk_url_scraper import VkScraper

from auto_archiver.utils.misc import dump_payload
from auto_archiver.core import Extractor
from auto_archiver.core import Metadata, Media


class VkExtractor(Extractor):
    """ "
    VK videos are handled by YTDownloader, this archiver gets posts text and images.
    Currently only works for /wall posts
    """

    def setup(self) -> None:
        self.vks = VkScraper(self.username, self.password, session_file=self.session_file)

    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()

        if "vk.com" not in item.netloc:
            return False

        # some urls can contain multiple wall/photo/... parts and all will be fetched
        vk_scrapes = self.vks.scrape(url)
        if not len(vk_scrapes):
            return False
        logger.debug(f"VK: got {len(vk_scrapes)} scraped instances")

        result = Metadata()
        for scrape in vk_scrapes:
            if not result.get_title():
                result.set_title(scrape["text"])
            if not result.get_timestamp():
                result.set_timestamp(scrape["datetime"])

        result.set_content(dump_payload(vk_scrapes))

        filenames = self.vks.download_media(vk_scrapes, self.tmp_dir)
        for filename in filenames:
            result.add_media(Media(filename))

        return result.success("vk")
