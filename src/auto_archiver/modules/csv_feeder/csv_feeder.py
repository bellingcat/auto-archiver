from loguru import logger
import csv

from auto_archiver.core import Feeder
from auto_archiver.core import Metadata
from auto_archiver.utils import url_or_none

class CSVFeeder(Feeder):

    def __iter__(self) -> Metadata:
        url_column = self.column or 0
        for file in self.files:
            with open(file, "r") as f:
                reader = csv.reader(f)
                first_row = next(reader)
                if not(url_or_none(first_row[url_column])):
                    # it's a header row, skip it
                    logger.debug(f"Skipping header row: {first_row}")
                for row in reader:
                    url = row[0]
                    logger.debug(f"Processing {url}")
                    yield Metadata().set_url(url)