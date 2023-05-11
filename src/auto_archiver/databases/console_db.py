from loguru import logger

from . import Database
from ..core import Metadata


class ConsoleDb(Database):
    """
        Outputs results to the console
    """
    name = "console_db"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {}

    def started(self, item: Metadata) -> None:
        logger.warning(f"STARTED {item}")

    def failed(self, item: Metadata) -> None:
        logger.error(f"FAILED {item}")

    def aborted(self, item: Metadata) -> None:
        logger.warning(f"ABORTED {item}")

    def done(self, item: Metadata) -> None:
        """archival result ready - should be saved to DB"""
        logger.success(f"DONE {item}")