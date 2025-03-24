from loguru import logger

from auto_archiver.core.feeder import Feeder
from auto_archiver.core.metadata import Metadata
from auto_archiver.core.consts import SetupError


class CLIFeeder(Feeder):
    def setup(self) -> None:
        self.urls = self.config["urls"]
        if not self.urls:
            raise SetupError(
                "No URLs provided. Please provide at least one URL via the command line, or set up an alternative feeder. Use --help for more information."
            )

    def __iter__(self) -> Metadata:
        urls = self.config["urls"]
        for url in urls:
            logger.debug(f"Processing {url}")
            m = Metadata().set_url(url)
            yield m

        logger.success(f"Processed {len(urls)} URL(s)")
