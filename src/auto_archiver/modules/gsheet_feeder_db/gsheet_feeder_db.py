"""
GsheetsFeeder: A Google Sheets-based feeder for the Auto Archiver.

This reads data from Google Sheets and filters rows based on user-defined rules.
The filtered rows are processed into `Metadata` objects.

### Key properties
- validates the sheet's structure and filters rows based on input configurations.
- Ensures only rows with valid URLs and unprocessed statuses are included.
"""

import os
import traceback
from typing import Tuple, Union, Iterator
from urllib.parse import quote

import gspread
from auto_archiver.utils.custom_logger import logger
from slugify import slugify
from retrying import retry

from auto_archiver.core import Feeder, Database, Media
from auto_archiver.core import Metadata
from auto_archiver.modules.gsheet_feeder_db import GWorksheet
from auto_archiver.utils.misc import get_current_timestamp


class GsheetsFeederDB(Feeder, Database):
    def setup(self) -> None:
        self.gsheets_client = gspread.service_account(filename=self.service_account)
        # TODO mv to validators
        if not self.sheet and not self.sheet_id:
            raise ValueError("You need to define either a 'sheet' name or a 'sheet_id' in your manifest.")

    @retry(
        wait_exponential_multiplier=1,
        stop_max_attempt_number=6,
    )
    def open_sheet(self) -> gspread.Spreadsheet:
        if self.sheet:
            return self.gsheets_client.open(self.sheet)
        else:
            return self.gsheets_client.open_by_key(self.sheet_id)

    @retry(
        wait_exponential_multiplier=1,
        stop_max_attempt_number=6,
    )
    def enumerate_sheets(self, sheet) -> Iterator[gspread.Worksheet]:
        for worksheet in sheet.worksheets():
            yield worksheet

    def __iter__(self) -> Iterator[Metadata]:
        spreadsheet = self.open_sheet()
        for worksheet in self.enumerate_sheets(spreadsheet):
            with logger.contextualize(worksheet=f"{spreadsheet.title}:{worksheet.title}"):
                if not self.should_process_sheet(worksheet.title):
                    logger.debug("Skipped worksheet due to allow/block rules")
                    continue
                logger.info(f"Opening worksheet header={self.header}")
                gw = GWorksheet(worksheet, header_row=self.header, columns=self.columns)
                if len(missing_cols := self.missing_required_columns(gw)):
                    logger.debug(f"Skipped worksheet due to missing required column(s) for {missing_cols}")
                    continue

                # process and yield metadata here:
                yield from self._process_rows(gw)
            logger.info(f"Finished worksheet {worksheet.title}")

    def _process_rows(self, gw: GWorksheet):
        for row in range(1 + self.header, gw.count_rows() + 1):
            url = gw.get_cell(row, "url").strip()
            if not len(url):
                continue
            original_status = gw.get_cell(row, "status")
            status = gw.get_cell(row, "status", fresh=original_status in ["", None])
            # TODO: custom status parser(?) aka should_retry_from_status
            if status not in ["", None]:
                continue

            # All checks done - archival process starts here
            m = Metadata().set_url(url)
            self._set_context(m, gw, row)

            with logger.contextualize(row=row):
                yield m

    def _set_context(self, m: Metadata, gw: GWorksheet, row: int) -> Metadata:
        # TODO: Check folder value not being recognised
        m.set_context("gsheet", {"row": row, "worksheet": gw})

        if gw.get_cell_or_default(row, "folder", "") is None:
            folder = ""
        else:
            folder = slugify(gw.get_cell_or_default(row, "folder", "").strip())
        if len(folder):
            if self.use_sheet_names_in_stored_paths:
                m.set_context("folder", os.path.join(folder, slugify(self.sheet), slugify(gw.wks.title)))
            else:
                m.set_context("folder", folder)

    def should_process_sheet(self, sheet_name: str) -> bool:
        if len(self.allow_worksheets) and sheet_name not in self.allow_worksheets:
            # ALLOW rules exist AND sheet name not explicitly allowed
            return False
        return not (self.block_worksheets and sheet_name in self.block_worksheets)

    def missing_required_columns(self, gw: GWorksheet) -> list:
        missing = []
        for required_col in ["url", "status"]:
            if not gw.col_exists(required_col):
                missing.append(required_col)
        return missing

    def started(self, item: Metadata) -> None:
        logger.info("STARTED")
        gw, row = self._retrieve_gsheet(item)
        gw.set_cell(row, "status", "Archive in progress")

    def failed(self, item: Metadata, reason: str) -> None:
        logger.error("FAILED")
        self._safe_status_update(item, f"Archive failed {reason}")

    def aborted(self, item: Metadata) -> None:
        logger.warning("ABORTED")
        self._safe_status_update(item, "")

    def fetch(self, item: Metadata) -> Union[Metadata, bool]:
        """check if the given item has been archived already"""
        return False

    def done(self, item: Metadata, cached: bool = False) -> None:
        """archival result ready - should be saved to DB"""
        gw, row = self._retrieve_gsheet(item)

        cell_updates = []
        row_values = gw.get_row(row)

        logger.info("DONE")

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

        if (screenshot := item.get_media_by_id("screenshot")) and hasattr(screenshot, "urls"):
            batch_if_valid("screenshot", "\n".join(screenshot.urls))

        if (thumbnail := item.get_first_image("thumbnail")) and hasattr(thumbnail, "urls"):
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

        @retry(
            wait_exponential_multiplier=1,
            stop_max_attempt_number=5,
        )
        def batch_set_cell_with_retry(gw, cell_updates: list):
            gw.batch_set_cell(cell_updates)

        batch_set_cell_with_retry(gw, cell_updates)

    def _safe_status_update(self, item: Metadata, new_status: str) -> None:
        try:
            gw, row = self._retrieve_gsheet(item)
            gw.set_cell(row, "status", new_status)
        except Exception as e:
            logger.debug(f"Unable to update sheet: {e}: {traceback.format_exc()}")

    def _retrieve_gsheet(self, item: Metadata) -> Tuple[GWorksheet, int]:
        if gsheet := item.get_context("gsheet"):
            gw: GWorksheet = gsheet.get("worksheet")
            row: int = gsheet.get("row")
        elif self.sheet_id:
            logger.error("Unable to retrieve Gsheet, GsheetDB must be used alongside GsheetFeeder.")

        return gw, row
