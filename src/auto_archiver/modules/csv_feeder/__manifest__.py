{
    "name": "CSV Feeder",
    "type": ["feeder"],
    "requires_setup": False,
    "dependencies": {
        "python": ["loguru"],
        "bin": [""]
    },
    'requires_setup': True,
    'entry_point': "csv_feeder::CSVFeeder",
    "configs": {
            "files": {
                "default": None,
                "help": "Path to the input file(s) to read the URLs from, comma separated. \
                        Input files should be formatted with one URL per line",
                "required": True,
                "type": "valid_file",
                "nargs": "+",
            },
            "column": {
                "default": None,
                "help": "Column number or name to read the URLs from, 0-indexed",
            }
        },
    "description": """
    Reads URLs from CSV files and feeds them into the archiving process.

    ### Features
    - Supports reading URLs from multiple input files, specified as a comma-separated list.
    - Allows specifying the column number or name to extract URLs from.
    - Skips header rows if the first value is not a valid URL.

    ### Setu N
    - Input files should be formatted with one URL per line.
    """
}
