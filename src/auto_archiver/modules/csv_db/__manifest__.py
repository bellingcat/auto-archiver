{
    "name": "CSV Database",
    "type": ["database"],
    "requires_setup": False,
    "dependencies": {"python": ["loguru"]},
    "entry_point": "csv_db::CSVDb",
    "configs": {
        "csv_file": {"default": "db.csv", "help": "CSV file name to save metadata to"},
    },
    "description": """
Handles exporting archival results to a CSV file.

### Features
- Saves archival metadata as rows in a CSV file.
- Automatically creates the CSV file with a header if it does not exist.
- Appends new metadata entries to the existing file.

### Setup
Required config:
- csv_file: Path to the CSV file where results will be stored (default: "db.csv").
""",
}
