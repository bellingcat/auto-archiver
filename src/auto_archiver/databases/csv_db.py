import os
from loguru import logger
from csv import DictWriter
from dataclasses import asdict

from . import Database
from ..core import Metadata


class CSVDb(Database):
    """
        Outputs results to a CSV file
    """
    name = "csv_db"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        self.assert_valid_string("csv_file")

    @staticmethod
    def configs() -> dict:
        return {
            "csv_file": {"default": "db.csv", "help": "CSV file name"}
        }

    def done(self, item: Metadata) -> None:
        """archival result ready - should be saved to DB"""
        logger.success(f"DONE {item}")
        is_empty = not os.path.isfile(self.csv_file) or os.path.getsize(self.csv_file) == 0
        with open(self.csv_file, "a", encoding="utf-8") as outf:
            writer = DictWriter(outf, fieldnames=asdict(Metadata()))
            if is_empty: writer.writeheader()
            writer.writerow(asdict(item))
