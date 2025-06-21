from auto_archiver.utils.custom_logger import logger

from auto_archiver.core import Database
from auto_archiver.core import Metadata


class ConsoleDb(Database):
    """
    Outputs results to the console
    """

    def started(self, item: Metadata) -> None:
        logger.info(f"STARTED {item}")

    def failed(self, item: Metadata, reason: str) -> None:
        logger.error(f"FAILED {item}: {reason}")

    def aborted(self, item: Metadata) -> None:
        logger.warning(f"ABORTED {item}")

    def done(self, item: Metadata, cached: bool = False) -> None:
        """archival result ready - should be saved to DB"""
        logger.success(f"DONE {item}")
