{
    "name": "Google Sheets Feeder",
    "type": ["feeder"],
    "entry_point": "gsheet_feeder::GsheetsFeeder",
    "requires_setup": True,
    "dependencies": {
        "python": ["loguru", "gspread", "slugify"],
    },
    "configs": {
        "sheet": {"default": None, "help": "name of the sheet to archive"},
        "sheet_id": {
            "default": None,
            "help": "the id of the sheet to archive (alternative to 'sheet' config)",
        },
        "header": {"default": 1, "help": "index of the header row (starts at 1)", "type": "int"},
        "service_account": {
            "default": "secrets/service_account.json",
            "help": "service account JSON file path. Learn how to create one: https://gspread.readthedocs.io/en/latest/oauth2.html",
            "required": True,
        },
        "columns": {
            "default": {
                "url": "link",
                "status": "archive status",
                "folder": "destination folder",
                "archive": "archive location",
                "date": "archive date",
                "thumbnail": "thumbnail",
                "timestamp": "upload timestamp",
                "title": "upload title",
                "text": "text content",
                "screenshot": "screenshot",
                "hash": "hash",
                "pdq_hash": "perceptual hashes",
                "wacz": "wacz",
                "replaywebpage": "replaywebpage",
            },
            "help": "Custom names for the columns in your Google sheet. If you don't want to use the default column names, change them with this setting",
            "type": "json_loader",
        },
        "allow_worksheets": {
            "default": set(),
            "help": "A list of worksheet names that should be processed (overrides worksheet_block), leave empty so all are allowed",
        },
        "block_worksheets": {
            "default": set(),
            "help": "A list of worksheet names for worksheets that should be explicitly blocked from being processed",
        },
        "use_sheet_names_in_stored_paths": {
            "default": True,
            "help": "if True the stored files path will include 'workbook_name/worksheet_name/...'",
            "type": "bool",
        },
    },
    "description": """
    GsheetsFeeder 
    A Google Sheets-based feeder for the Auto Archiver.

    This reads data from Google Sheets and filters rows based on user-defined rules.
    The filtered rows are processed into `Metadata` objects.

    ### Features
    - Validates the sheet structure and filters rows based on input configurations.
    - Processes only worksheets allowed by the `allow_worksheets` and `block_worksheets` configurations.
    - Ensures only rows with valid URLs and unprocessed statuses are included for archival.
    - Supports organizing stored files into folder paths based on sheet and worksheet names.

    ### Setup
    - Requires a Google Service Account JSON file for authentication, which should be stored in `secrets/gsheets_service_account.json`.
    To set up a service account, follow the instructions [here](https://gspread.readthedocs.io/en/latest/oauth2.html).
    - Define the `sheet` or `sheet_id` configuration to specify the sheet to archive.
    - Customize the column names in your Google sheet using the `columns` configuration.
    """,
}
