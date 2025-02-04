{
    "name": "Example Module",
    "type": ["extractor", "feeder", "formatter", "storage", "enricher", "database"],
    "requires_setup": False,
    "dependencies": {"python": ["loguru"]
                              },
    "configs": {
            "csv_file": {"default": "db.csv", "help": "CSV file name"},
            "required_field": {"required": True, "help": "required field in the CSV file"},
        },
}