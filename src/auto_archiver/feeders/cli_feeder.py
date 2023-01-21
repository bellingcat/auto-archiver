import gspread, os

# from metadata import Metadata
from loguru import logger

# from . import Enricher
from . import Feeder
from ..core import Metadata


class CLIFeeder(Feeder):
    name = "cli_feeder"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        assert type(self.urls) == list and len(self.urls) > 0, "Please provide a CSV list of URL(s) to process, with --cli_feeder.urls='url1,url2,url3'"

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
            yield Metadata().set_url(url).set("folder", "cli", True)
        logger.success(f"Processed {len(self.urls)} URL(s)")
