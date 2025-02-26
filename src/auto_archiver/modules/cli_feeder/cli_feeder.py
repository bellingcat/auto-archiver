from loguru import logger

from auto_archiver.core.feeder import Feeder
from auto_archiver.core.metadata import Metadata

class CLIFeeder(Feeder):

    def __iter__(self) -> Metadata:
        urls = self.config['urls']
        for url in urls:
            logger.debug(f"Processing {url}")
            m = Metadata().set_url(url)
            m.set_context("folder", "cli")
            yield m

        logger.success(f"Processed {len(urls)} URL(s)")