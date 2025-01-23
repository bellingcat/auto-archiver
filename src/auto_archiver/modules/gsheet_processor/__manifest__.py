{
    "name": "Google Sheets Procesor",
    "type": ["feeder"],
    "requires_setup": True,
    "external_dependencies": {
        "python": ["loguru", "gspread", "python-slugify"],
    },
    "configs": {
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
    },
    "description": """
    Google Sheets Module.
    
    Handles feeding from a google sheet as well as an optional write back to the sheet.
    
    ## GsheetsFeeder 
    A Google Sheets-based feeder for the Auto Archiver.

    This reads data from Google Sheets and filters rows based on user-defined rules.
    The filtered rows are processed into `Metadata` objects.

    ### Features
    - Validates the sheet structure and filters rows based on input configurations.
    - Processes only worksheets allowed by the `allow_worksheets` and `block_worksheets` configurations.
    - Ensures only rows with valid URLs and unprocessed statuses are included for archival.
    - Supports organizing stored files into folder paths based on sheet and worksheet names.

    ### Notes
    - Requires a Google Service Account JSON file for authentication. Suggested location is `secrets/gsheets_service_account.json`.
    - Create the sheet using the template provided in the docs.
    
    ## GsheetsDatabase:
    Handles integration with Google Sheets for tracking archival tasks.

### Features
- Updates a Google Sheet with the status of the archived URLs, including in progress, success or failure, and method used.
- Saves metadata such as title, text, timestamp, hashes, screenshots, and media URLs to designated columns.
- Formats media-specific metadata, such as thumbnails and PDQ hashes for the sheet.
- Skips redundant updates for empty or invalid data fields.

### Notes
- Currently works only with metadata provided by GsheetFeeder. 
- Requires configuration of a linked Google Sheet and appropriate API credentials.
    """
}
