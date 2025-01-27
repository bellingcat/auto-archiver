from loguru import logger

from auto_archiver.base_processors import Feeder
from auto_archiver.core import Metadata, ArchivingContext


class CLIFeeder(Feeder):
    name = "cli_feeder"

    def __iter__(self) -> Metadata:
        for url in self.urls:
            logger.debug(f"Processing {url}")
            yield Metadata().set_url(url)
            ArchivingContext.set("folder", "cli")

        logger.success(f"Processed {len(self.urls)} URL(s)")
