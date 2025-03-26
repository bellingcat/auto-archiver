from auto_archiver.core import Extractor, Enricher, Feeder, Database, Storage, Formatter, Metadata

from loguru import logger


class ExampleModule(Extractor, Enricher, Feeder, Database, Storage, Formatter):
    def download(self, item):
        logger.info("download")

    def __iter__(self):
        yield Metadata().set_url("https://example.com")

    def done(self, result):
        logger.info("done")

    def enrich(self, to_enrich):
        logger.info("enrich")

    def get_cdn_url(self, media):
        return "nice_url"

    def save(self, item):
        logger.info("save")

    def uploadf(self, file, key, **kwargs):
        logger.info("uploadf")

    def format(self, item):
        logger.info("format")
