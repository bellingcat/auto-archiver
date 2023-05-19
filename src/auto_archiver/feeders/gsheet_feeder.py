import gspread, os

from loguru import logger
from slugify import slugify

# from . import Enricher
from . import Feeder
from ..core import Metadata, ArchivingContext
from ..utils import Gsheets, GWorksheet


class GsheetsFeeder(Gsheets, Feeder):
    name = "gsheet_feeder"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        self.gsheets_client = gspread.service_account(filename=self.service_account)

    @staticmethod
    def configs() -> dict:
        return dict(
            Gsheets.configs(),
            ** {
                "allow_worksheets": {
                    "default": set(),
                    "help": "(CSV) only worksheets whose name is included in allow are included (overrides worksheet_block), leave empty so all are allowed",
                    "cli_set": lambda cli_val, cur_val: set(cli_val.split(","))
                },
                "block_worksheets": {
                    "default": set(),
                    "help": "(CSV) explicitly block some worksheets from being processed",
                    "cli_set": lambda cli_val, cur_val: set(cli_val.split(","))
                },
                "use_sheet_names_in_stored_paths": {
                    "default": True,
                    "help": "if True the stored files path will include 'workbook_name/worksheet_name/...'",
                }
            })

    def __iter__(self) -> Metadata:
        sh = self.open_sheet()
        for ii, wks in enumerate(sh.worksheets()):
            if not self.should_process_sheet(wks.title):
                logger.debug(f"SKIPPED worksheet '{wks.title}' due to allow/block rules")
                continue

            logger.info(f'Opening worksheet {ii=}: {wks.title=} header={self.header}')
            gw = GWorksheet(wks, header_row=self.header, columns=self.columns)

            if len(missing_cols := self.missing_required_columns(gw)):
                logger.warning(f"SKIPPED worksheet '{wks.title}' due to missing required column(s) for {missing_cols}")
                continue

            for row in range(1 + self.header, gw.count_rows() + 1):
                url = gw.get_cell(row, 'url').strip()
                if not len(url): continue

                original_status = gw.get_cell(row, 'status')
                status = gw.get_cell(row, 'status', fresh=original_status in ['', None])
                # TODO: custom status parser(?) aka should_retry_from_status
                if status not in ['', None]: continue

                # All checks done - archival process starts here
                m = Metadata().set_url(url)
                ArchivingContext.set("gsheet", {"row": row, "worksheet": gw}, keep_on_reset=True)
                folder = slugify(gw.get_cell(row, 'folder').strip())
                if len(folder):
                    if self.use_sheet_names_in_stored_paths:
                        ArchivingContext.set("folder", os.path.join(folder, slugify(self.sheet), slugify(wks.title)), True)
                    else:
                        ArchivingContext.set("folder", folder, True)

                yield m

            logger.success(f'Finished worksheet {wks.title}')

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
