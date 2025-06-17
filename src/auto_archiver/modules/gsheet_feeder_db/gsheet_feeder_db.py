"""
GsheetsFeeder: A Google Sheets-based feeder for the Auto Archiver.

This reads data from Google Sheets and filters rows based on user-defined rules.
The filtered rows are processed into `Metadata` objects.

### Key properties
- validates the sheet's structure and filters rows based on input configurations.
- Ensures only rows with valid URLs and unprocessed statuses are included.
"""

import os
import time
from typing import Tuple, Union
from urllib.parse import quote

import gspread
from loguru import logger
from slugify import slugify

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

    def open_sheet(self):
        if self.sheet:
            return self.gsheets_client.open(self.sheet)
        else:  # self.sheet_id
            return self.gsheets_client.open_by_key(self.sheet_id)

    def __iter__(self) -> Metadata:
        # This is the 1.Feeder step ie opening the spreadsheet and iterating over the worksheets
        sh = self.open_sheet()
        for ii, worksheet in enumerate(sh.worksheets()):
            if not self.should_process_sheet(worksheet.title):
                logger.debug(f"SKIPPED worksheet '{worksheet.title}' due to allow/block rules")
                continue
            logger.info(f"Opening worksheet {ii=}: {worksheet.title=} header={self.header}")
            gw = GWorksheet(worksheet, header_row=self.header, columns=self.columns)
            if len(missing_cols := self.missing_required_columns(gw)):
                logger.warning(
                    f"SKIPPED worksheet '{worksheet.title}' due to missing required column(s) for {missing_cols}"
                )
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

            # Set in orchestration.yaml. Default is False
            if self.must_have_folder_name_for_archive_to_run:
                if not gw.get_cell(row, "folder"):
                    logger.warning(f"Folder name not set {self.sheet}:{gw.wks.title}, row {row} - skipping and continuing with run")
                    gw.set_cell(row, "status", "WARNING:Folder Name not set")
                    continue

            # All checks done - archival process starts here
            m = Metadata().set_url(url)
            self._set_context(m, gw, row)
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
        logger.info(f"STARTED {item}")
        gw, row = self._retrieve_gsheet(item)
        gw.set_cell(row, "status", "Archive in progress")
        logger.info(f" row: {row} on {gw.wks.spreadsheet.title} : {gw.wks.title}")

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

        # DM - success log message showing the row, sheet and tab
        spreadsheet = gw.wks.spreadsheet.title
        worksheet = gw.wks.title
        logger.success(f" row {row} on {spreadsheet} : {worksheet}")

        cell_updates = []
        row_values = gw.get_row(row)

        def batch_if_valid(col, val, final_value=None):
            final_value = final_value or val
            try:
                if self.allow_overwrite_of_spreadsheet_cells:
                    if val and gw.col_exists(col):
                        existing_value = gw.get_cell(row_values, col)
                        if existing_value:
                            logger.info(f"Overwriting spreadsheet cell {col}={existing_value} with {final_value} in {gw.wks.title} row {row}")
                        cell_updates.append((row, col, final_value))
                else:
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

        # DM 4th Jun 25 - saw this fail with a google api [503]: The service is currently unavailable.
        # so added a retry loop.
        attempt = 1
        while attempt <= 5:
            try:
                gw.batch_set_cell(cell_updates)
                break
            except Exception as e:
                logger.warning(f"Attempt {attempt} of batch_set_cell failed due to {e} ")
                attempt += 1
                time.sleep(5 * attempt) # linear backoff

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
            logger.error(
                f"Unable to retrieve Gsheet for {item.get_url()}, GsheetDB must be used alongside GsheetFeeder."
            )

        return gw, row
