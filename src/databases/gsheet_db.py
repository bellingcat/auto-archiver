from typing import Union, Tuple
import gspread

# from metadata import Metadata
from loguru import logger

# from . import Enricher
from databases import Database
from metadata import Metadata
from steps.gsheet import Gsheets
from utils import GWorksheet


class GsheetsDb(Database):
    """
        NB: only works if GsheetFeeder is used. 
        could be updated in the future to support non-GsheetFeeder metadata 
    """
    name = "gsheet_db"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {}

    def started(self, item: Metadata) -> None:
        logger.warning(f"STARTED {item}")
        gw, row = self._retrieve_gsheet(item)
        gw.set_cell(row, 'status', 'Archive in progress')

    def failed(self, item: Metadata) -> None:
        logger.error(f"FAILED {item}")
        self._safe_status_update(item, 'Archive failed')

    def aborted(self, item: Metadata) -> None:
        logger.warning(f"ABORTED {item}")
        self._safe_status_update(item, '')

    def fetch(self, item: Metadata) -> Union[Metadata, bool]:
        """check if the given item has been archived already"""
        # TODO: this should not be done at the feeder stage then!
        return False

    def done(self, item: Metadata) -> None:
        """archival result ready - should be saved to DB"""
        logger.success(f"DONE {item}")
        gw, row = self._retrieve_gsheet(item)
        self._safe_status_update(item, 'done')
        pass

    def _safe_status_update(self, item: Metadata, new_status: str) -> None:
        try:
            gw, row = self._retrieve_gsheet(item)
            gw.set_cell(row, 'status', new_status)
        except Exception as e:
            logger.debug(f"Unable to update sheet: {e}")

    def _retrieve_gsheet(self, item: Metadata) -> Tuple[GWorksheet, int]:
        gw: GWorksheet = item.get("gsheet").get("worksheet")
        row: int = item.get("gsheet").get("row")
        return gw, row
