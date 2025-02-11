{
    # Display Name of your module
    "name": "Example Module",
    # The author of your module (optional)
    "author": "John Doe",
    # Optional version number, for your own versioning purposes
    "version": 2.0,
    # The type of the module, must be one (or more) of the built in module types
    "type": ["extractor", "feeder", "formatter", "storage", "enricher", "database"],
    # a boolean indicating whether or not a module requires additional user setup before it can be used
    # for example: adding API keys, installing additional software etc.
    "requires_setup": False,
    # a dictionary of dependencies for this module, that must be installed before the module is loaded.
    # Can be python dependencies (external packages, or other auto-archiver modules), or you can
    # provide external bin dependencies (e.g. ffmpeg, docker etc.)
    "dependencies": {
        "python": ["loguru"],
        "bin": ["bash"],
        },
    # configurations that this module takes. These are argparse-compliant dicationaries, that are 
    # used to create command line arguments when the programme is run.
    # The full name of the config option will become: `module_name.config_name`
    "configs": {
            "csv_file": {"default": "db.csv", "help": "CSV file name"},
            "required_field": {"required": True, "help": "required field in the CSV file"},
        },
    # A description of the module, used for documentation
    "description": "This is an example module",
}