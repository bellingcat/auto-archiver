{
    "name": "Example Module",
    "type": ["extractor"],
    "requires_setup": False,
    "external_dependencies": {"python": ["loguru"]
                              },
    "configs": {
            "csv_file": {"default": "db.csv", "help": "CSV file name"}
        },
}