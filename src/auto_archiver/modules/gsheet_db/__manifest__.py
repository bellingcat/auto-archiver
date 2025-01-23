# TODO merge with feeder manifest?
{
    "name": "gsheet_db",
    "type": ["database"],
    "requires_setup": True,
    "external_dependencies": {"python": [" loguru"],
                              },
    "description": """
Handles integration with Google Sheets for tracking archival tasks.

### Features
- Updates a Google Sheet with the status of the archived URLs, including in progress, success or failure, and method used.
- Saves metadata such as title, text, timestamp, hashes, screenshots, and media URLs to designated columns.
- Formats media-specific metadata, such as thumbnails and PDQ hashes for the sheet.
- Skips redundant updates for empty or invalid data fields.

### Notes
- Currently works only with metadata provided by GsheetFeeder. 
- Requires configuration of a linked Google Sheet and appropriate API credentials.
""",
}
