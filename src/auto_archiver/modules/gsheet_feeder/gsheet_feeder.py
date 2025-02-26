"""
GsheetsFeeder: A Google Sheets-based feeder for the Auto Archiver.

This reads data from Google Sheets and filters rows based on user-defined rules.
The filtered rows are processed into `Metadata` objects.

### Key properties
- validates the sheet's structure and filters rows based on input configurations.
- Ensures only rows with valid URLs and unprocessed statuses are included.
"""
import os
import gspread

from loguru import logger
from slugify import slugify

from auto_archiver.core import Feeder
from auto_archiver.core import Metadata
from . import GWorksheet


class GsheetsFeeder(Feeder):

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
        sh = self.open_sheet()
        for ii, worksheet in enumerate(sh.worksheets()):
            if not self.should_process_sheet(worksheet.title):
                logger.debug(f"SKIPPED worksheet '{worksheet.title}' due to allow/block rules")
                continue
            logger.info(f'Opening worksheet {ii=}: {worksheet.title=} header={self.header}')
            gw = GWorksheet(worksheet, header_row=self.header, columns=self.columns)
            if len(missing_cols := self.missing_required_columns(gw)):
                logger.warning(f"SKIPPED worksheet '{worksheet.title}' due to missing required column(s) for {missing_cols}")
                continue

            # process and yield metadata here:
            yield from self._process_rows(gw)
            logger.success(f'Finished worksheet {worksheet.title}')

    def _process_rows(self, gw: GWorksheet):
        for row in range(1 + self.header, gw.count_rows() + 1):
            url = gw.get_cell(row, 'url').strip()
            if not len(url): continue
            original_status = gw.get_cell(row, 'status')
            status = gw.get_cell(row, 'status', fresh=original_status in ['', None])
            # TODO: custom status parser(?) aka should_retry_from_status
            if status not in ['', None]: continue

            # All checks done - archival process starts here
            m = Metadata().set_url(url)
            self._set_context(m, gw, row)
            yield m

    def _set_context(self, m: Metadata, gw: GWorksheet, row: int) -> Metadata:

        m.set_context("gsheet", {"row": row, "worksheet": gw})

        if gw.get_cell_or_default(row, 'folder', "") is None:
            folder = ''
        else:
            folder = slugify(gw.get_cell_or_default(row, 'folder', "").strip())
        if len(folder):
            if self.use_sheet_names_in_stored_paths:
                m.set_context("folder", os.path.join(folder, slugify(self.sheet), slugify(gw.wks.title)))
            else:
                m.set_context("folder", folder)


    def should_process_sheet(self, sheet_name: str) -> bool:
        if len(self.allow_worksheets) and sheet_name not in self.allow_worksheets:
            # ALLOW rules exist AND sheet name not explicitly allowed
            return False
        if len(self.block_worksheets) and sheet_name in self.block_worksheets:
            # BLOCK rules exist AND sheet name is blocked
            return False
        return True

    def missing_required_columns(self, gw: GWorksheet) -> list:
        missing = []
        for required_col in ['url', 'status']:
            if not gw.col_exists(required_col):
                missing.append(required_col)
        return missing
