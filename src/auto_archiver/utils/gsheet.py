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

    @staticmethod
    def configs() -> dict:
        return {
            "sheet": {"default": None, "help": "name of the sheet to archive"},
            "sheet_id": {"default": None, "help": "(alternative to sheet name) the id of the sheet to archive"},
            "header": {"default": 1, "help": "index of the header row (starts at 1)"},
            "service_account": {"default": "secrets/service_account.json", "help": "service account JSON file path"},
            "columns": {
                "default": {
                    'url': 'link',
                    'status': 'archive status',
                    'folder': 'destination folder',
                    'archive': 'archive location',
                    'date': 'archive date',
                    'thumbnail': 'thumbnail',
                    'timestamp': 'upload timestamp',
                    'title': 'upload title',
                    'text': 'text content',
                    'screenshot': 'screenshot',
                    'hash': 'hash',
                    'wacz': 'wacz',
                    'replaywebpage': 'replaywebpage',
                },
                "help": "names of columns in the google sheet (stringified JSON object)",
                "cli_set": lambda cli_val, cur_val: dict(cur_val, **json.loads(cli_val))
            },
        }

    def open_sheet(self):
        if self.sheet:
            return self.gsheets_client.open(self.sheet)
        else:  # self.sheet_id
            return self.gsheets_client.open_by_key(self.sheet_id)
