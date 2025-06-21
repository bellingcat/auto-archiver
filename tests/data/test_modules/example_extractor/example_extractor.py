from auto_archiver.core import Extractor

from auto_archiver.utils.custom_logger import logger


class ExampleExtractor(Extractor):
    def download(self, item):
        logger.info("download")

    def cleanup(self):
        logger.info("cleanup")
