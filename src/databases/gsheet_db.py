from typing import Union, Tuple
import gspread, datetime

# from metadata import Metadata
from loguru import logger

# from . import Enricher
from databases import Database
from metadata import Metadata
from media import Media
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
        # self._safe_status_update(item, 'done')

        cell_updates = []
        row_values = gw.get_row(row)

        def batch_if_valid(col, val, final_value=None):
            final_value = final_value or val
            if val and gw.col_exists(col) and gw.get_cell(row_values, col) == '':
                cell_updates.append((row, col, final_value))

        cell_updates.append((row, 'status', item.status))

        media: Media = item.get_single_media()

        batch_if_valid('archive', media.cdn_url)
        batch_if_valid('date', True, datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat())
        batch_if_valid('title', item.get_title())
        batch_if_valid('text', item.get("content", "")[:500])
        batch_if_valid('timestamp', item.get_timestamp())

        # TODO: AFTER ENRICHMENTS
        # batch_if_valid('hash', media.hash)
        # batch_if_valid('thumbnail', result.thumbnail, f'=IMAGE("{result.thumbnail}")')
        # batch_if_valid('thumbnail_index', result.thumbnail_index)
        # batch_if_valid('duration', result.duration, str(result.duration))
        # batch_if_valid('screenshot', result.screenshot)
        # if result.wacz is not None:
        #     batch_if_valid('wacz', result.wacz)
        #     batch_if_valid('replaywebpage', f'https://replayweb.page/?source={quote(result.wacz)}#view=pages&url={quote(url)}')

        gw.batch_set_cell(cell_updates)

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
