from typing import Union, Tuple
from urllib.parse import quote

from loguru import logger

from auto_archiver.core import Database
from auto_archiver.core import Metadata, Media
from auto_archiver.modules.gsheet_feeder import GWorksheet
from auto_archiver.utils.misc import get_current_timestamp


class GsheetsDb(Database):
    """
    NB: only works if GsheetFeeder is used.
    could be updated in the future to support non-GsheetFeeder metadata
    """

    def started(self, item: Metadata) -> None:
        logger.warning(f"STARTED {item}")
        gw, row = self._retrieve_gsheet(item)
        gw.set_cell(row, "status", "Archive in progress")

    def failed(self, item: Metadata, reason: str) -> None:
        logger.error(f"FAILED {item}")
        self._safe_status_update(item, f"Archive failed {reason}")

    def aborted(self, item: Metadata) -> None:
        logger.warning(f"ABORTED {item}")
        self._safe_status_update(item, "")

    def fetch(self, item: Metadata) -> Union[Metadata, bool]:
        """check if the given item has been archived already"""
        return False

    def done(self, item: Metadata, cached: bool = False) -> None:
        """archival result ready - should be saved to DB"""
        logger.success(f"DONE {item.get_url()}")
        gw, row = self._retrieve_gsheet(item)
        # self._safe_status_update(item, 'done')

        cell_updates = []
        row_values = gw.get_row(row)

        def batch_if_valid(col, val, final_value=None):
            final_value = final_value or val
            try:
                if val and gw.col_exists(col) and gw.get_cell(row_values, col) == "":
                    cell_updates.append((row, col, final_value))
            except Exception as e:
                logger.error(f"Unable to batch {col}={final_value} due to {e}")

        status_message = item.status
        if cached:
            status_message = f"[cached] {status_message}"
        cell_updates.append((row, "status", status_message))

        media: Media = item.get_final_media()
        if hasattr(media, "urls"):
            batch_if_valid("archive", "\n".join(media.urls))
        batch_if_valid("date", True, get_current_timestamp())
        batch_if_valid("title", item.get_title())
        batch_if_valid("text", item.get("content", ""))
        batch_if_valid("timestamp", item.get_timestamp())
        if media:
            batch_if_valid("hash", media.get("hash", "not-calculated"))

        # merge all pdq hashes into a single string, if present
        pdq_hashes = []
        all_media = item.get_all_media()
        for m in all_media:
            if pdq := m.get("pdq_hash"):
                pdq_hashes.append(pdq)
        if len(pdq_hashes):
            batch_if_valid("pdq_hash", ",".join(pdq_hashes))

        if (screenshot := item.get_media_by_id("screenshot")) and hasattr(
            screenshot, "urls"
        ):
            batch_if_valid("screenshot", "\n".join(screenshot.urls))

        if thumbnail := item.get_first_image("thumbnail"):
            if hasattr(thumbnail, "urls"):
                batch_if_valid("thumbnail", f'=IMAGE("{thumbnail.urls[0]}")')

        if browsertrix := item.get_media_by_id("browsertrix"):
            batch_if_valid("wacz", "\n".join(browsertrix.urls))
            batch_if_valid(
                "replaywebpage",
                "\n".join(
                    [
                        f"https://replayweb.page/?source={quote(wacz)}#view=pages&url={quote(item.get_url())}"
                        for wacz in browsertrix.urls
                    ]
                ),
            )

        gw.batch_set_cell(cell_updates)

    def _safe_status_update(self, item: Metadata, new_status: str) -> None:
        try:
            gw, row = self._retrieve_gsheet(item)
            gw.set_cell(row, "status", new_status)
        except Exception as e:
            logger.debug(f"Unable to update sheet: {e}")

    def _retrieve_gsheet(self, item: Metadata) -> Tuple[GWorksheet, int]:

        if gsheet := item.get_context("gsheet"):
            gw: GWorksheet = gsheet.get("worksheet")
            row: int = gsheet.get("row")
        elif self.sheet_id:
            print(self.sheet_id)

        return gw, row
