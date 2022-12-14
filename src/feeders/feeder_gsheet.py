import json, gspread

# from metadata import Metadata
from loguru import logger

# from . import Enricher
from feeders import Feeder
from steps.gsheet import Gsheets
from utils import GWorksheet


class GsheetsFeeder(Gsheets, Feeder):
    name = "gsheets_feeder"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        self.gsheets_client = gspread.service_account(filename=self.service_account)
        assert type(self.header) == int, f"header ({self.header}) value must be an integer not {type(self.header)}"

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
                }
            })

    def __iter__(self) -> str:
        sh = self.gsheets_client.open(self.sheet)
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
                # TODO: gsheet_db should check later if this is supposed to be archived
                # static_status = gw.get_cell(row, 'status')
                # status = gw.get_cell(row, 'status', fresh=static_status in ['', None] and url != '')
                # All checks done - archival process starts here
                yield url
            logger.success(f'Finished worksheet {wks.title}')

        # GWorksheet(self.sheet)
        print(self.sheet)
        for u in ["url1", "url2"]:
            yield u

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
