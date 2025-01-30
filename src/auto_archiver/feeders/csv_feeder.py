from loguru import logger
import csv

from . import Feeder
from ..core import Metadata
from ..utils import url_or_none

class CSVFeeder(Feeder):

    @staticmethod
    def configs() -> dict:
        return {
            "files": {
                "default": None,
                "help": "Path to the input file(s) to read the URLs from, comma separated. \
                        Input files should be formatted with one URL per line",
                "cli_set": lambda cli_val, cur_val: list(set(cli_val.split(",")))
            },
            "column": {
                "default": None,
                "help": "Column number or name to read the URLs from, 0-indexed",
            }
        }
    

    def __iter__(self) -> Metadata:
        url_column = self.column or 0
        for file in self.files:
            with open(file, "r") as f:
                reader = csv.reader(f)
                first_row = next(reader)
                if not(url_or_none(first_row[url_column])):
                    # it's a header row, skip it
                for row in reader:
                    url = row[0]
                    logger.debug(f"Processing {url}")
                    yield Metadata().set_url(url)