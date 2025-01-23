{
    "name": "CSV Feeder",
    "type": ["feeder"],
    "requires_setup": False,
    "external_dependencies": {
        "python": ["loguru"],
        "bin": [""]
    },
    "configs": {
            "files": {
                "default": None,
                "help": "Path to the input file(s) to read the URLs from, comma separated. \
                        Input files should be formatted with one URL per line",
                "cli_set": lambda cli_val, cur_val: list(set(cli_val.split(",")))
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
    - Integrates with the `ArchivingContext` to manage URL feeding.

    ### Setu N
    - Input files should be formatted with one URL per line.
    """
}
