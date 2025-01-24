import json, gspread

from ..core import Step


class Gsheets(Step):
    name = "gsheets"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        self.gsheets_client = gspread.service_account(filename=self.service_account)
        # TODO: config should be responsible for conversions
        try: self.header = int(self.header)
        except: pass
        assert type(self.header) == int, f"header ({self.header}) value must be an integer not {type(self.header)}"
        assert self.sheet is not None or self.sheet_id is not None, "You need to define either a 'sheet' name or a 'sheet_id' in your orchestration file when using gsheets."

    def open_sheet(self):
        if self.sheet:
            return self.gsheets_client.open(self.sheet)
        else:  # self.sheet_id
            return self.gsheets_client.open_by_key(self.sheet_id)
