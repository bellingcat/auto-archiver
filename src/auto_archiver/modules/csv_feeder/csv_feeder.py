from loguru import logger
import csv

from auto_archiver.core import Feeder
from auto_archiver.core import Metadata
from auto_archiver.utils import url_or_none


class CSVFeeder(Feeder):
    column = None

    def __iter__(self) -> Metadata:
        for file in self.files:
            with open(file, "r") as f:
                reader = csv.reader(f)
                first_row = next(reader)
                url_column = self.column or 0
                if isinstance(url_column, str):
                    try:
                        url_column = first_row.index(url_column)
                    except ValueError:
                        logger.error(
                            f"Column {url_column} not found in header row: {first_row}. Did you set the 'column' config correctly?"
                        )
                        return
                elif not (url_or_none(first_row[url_column])):
                    # it's a header row, but we've been given a column number already
                    logger.debug(f"Skipping header row: {first_row}")
                else:
                    # first row isn't a header row, rewind the file
                    f.seek(0)

                for row in reader:
                    if not url_or_none(row[url_column]):
                        logger.warning(f"Not a valid URL in row: {row}, skipping")
                        continue
                    url = row[url_column]
                    logger.debug(f"Processing {url}")
                    yield Metadata().set_url(url)
