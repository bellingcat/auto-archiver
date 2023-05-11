from loguru import logger

from . import Feeder
from ..core import Metadata, ArchivingContext


class CLIFeeder(Feeder):
    name = "cli_feeder"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        if type(self.urls) != list or len(self.urls) == 0:
            raise Exception("CLI Feeder did not receive any URL to process")

    @staticmethod
    def configs() -> dict:
        return {
            "urls": {
                "default": None,
                "help": "URL(s) to archive, either a single URL or a list of urls, should not come from config.yaml",
                "cli_set": lambda cli_val, cur_val: list(set(cli_val.split(",")))
            },
        }

    def __iter__(self) -> Metadata:
        for url in self.urls:
            logger.debug(f"Processing {url}")
            yield Metadata().set_url(url)
            ArchivingContext.set("folder", "cli")

        logger.success(f"Processed {len(self.urls)} URL(s)")
