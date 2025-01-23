m = {
    "name": "Local Storage",
    "type": ["storage"],
    "requires_setup": False,
    "external_dependencies": {
        "python": ["loguru"],
    },
    "configs": {
        "path_generator": {
            "default": "url",
            "help": "how to store the file in terms of directory structure: 'flat' sets to root; 'url' creates a directory based on the provided URL; 'random' creates a random directory.",
        },
        "filename_generator": {
            "default": "random",
            "help": "how to name stored files: 'random' creates a random string; 'static' uses a replicable strategy such as a hash.",
        },
        "save_to": {"default": "./archived", "help": "folder where to save archived content"},
        "save_absolute": {"default": False, "help": "whether the path to the stored file is absolute or relative in the output result inc. formatters (WARN: leaks the file structure)"},
    },
    "description": """
    LocalStorage: A storage module for saving archived content locally on the filesystem.

    ### Features
    - Saves archived media files to a specified folder on the local filesystem.
    - Maintains file metadata during storage using `shutil.copy2`.
    - Supports both absolute and relative paths for stored files, configurable via `save_absolute`.
    - Automatically creates directories as needed for storing files.

    ### Notes
    - Default storage folder is `./archived`, but this can be changed via the `save_to` configuration.
    - The `save_absolute` option can reveal the file structure in output formats; use with caution.
    """
}
