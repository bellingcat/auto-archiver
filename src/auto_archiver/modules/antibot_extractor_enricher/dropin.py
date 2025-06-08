from seleniumbase import SB

from auto_archiver.core.extractor import Extractor
from auto_archiver.core.metadata import Metadata


class Dropin:
    """
    A class to handle drop-in functionality for the antibot extractor enricher module.
    This class is designed to be a base class for drop-ins that can handle specific websites.
    """

    def __init__(self, sb: SB, extractor: Extractor):
        """
        Initialize the Dropin with the given SeleniumBase instance.

        :param sb: An instance of the SeleniumBase class that this drop-in will use.
        :param extractor: An instance of the Extractor class that this drop-in will use.
        """
        self.sb: SB = sb
        self.extractor: Extractor = extractor

    @staticmethod
    def suitable(url: str) -> bool:
        """
        Check if the URL is suitable for processing with this dropin.
        :param url: The URL to check.
        :return: True if the URL is suitable for processing, False otherwise.
        """
        raise NotImplementedError("This method should be implemented in the subclass")

    @staticmethod
    def sanitize_url(url: str) -> str:
        """
        Used to clean URLs before processing them.
        """
        return url

    def open_page(self, url) -> bool:
        """
        Make sure the page is opened, even if it requires authentication, captcha solving, etc.
        :param url: The URL to open.
        :return: True if success, False otherwise.
        """
        raise NotImplementedError("This method should be implemented in the subclass")

    def add_extra_media(self, to_enrich: Metadata) -> tuple[int, int]:
        """
        Extract image and/or video data from the currently open post with SeleniumBase. Media is added to the `to_enrich` Metadata object.
        :return: A tuple (number of Images added, number of Videos added).
        """
        raise NotImplementedError("This method should be implemented in the subclass")
