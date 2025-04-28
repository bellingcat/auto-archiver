
from auto_archiver.core import Extractor
from auto_archiver.core import Metadata
from auto_archiver.core import Media


class SeleniumExtractor(Extractor):
    def download(self, item: Metadata) -> Metadata | False:
        """
        Downloads the media from the given URL and returns a Metadata object with the downloaded media.

        If the URL is not supported or the download fails, this method should return False.

        """
        pass
