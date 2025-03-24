{
    "name": "S3 Storage",
    "type": ["storage"],
    "requires_setup": True,
    "dependencies": {
        "python": ["hash_enricher", "boto3", "loguru"],
    },
    "configs": {
        "path_generator": {
            "default": "flat",
            "help": "how to store the file in terms of directory structure: 'flat' sets to root; 'url' creates a directory based on the provided URL; 'random' creates a random directory.",
            "choices": ["flat", "url", "random"],
        },
        "filename_generator": {
            "default": "static",
            "help": "how to name stored files: 'random' creates a random string; 'static' uses a hash, with the settings of the 'hash_enricher' module (defaults to SHA256 if not enabled).",
            "choices": ["random", "static"],
        },
        "bucket": {"default": None, "help": "S3 bucket name"},
        "region": {"default": None, "help": "S3 region name"},
        "key": {"default": None, "help": "S3 API key"},
        "secret": {"default": None, "help": "S3 API secret"},
        "random_no_duplicate": {
            "default": False,
            "type": "bool",
            "help": "if set, it will override `path_generator`, `filename_generator` and `folder`. It will check if the file already exists and if so it will not upload it again. Creates a new root folder path `no-dups/`",
        },
        "endpoint_url": {
            "default": "https://{region}.digitaloceanspaces.com",
            "help": "S3 bucket endpoint, {region} are inserted at runtime",
        },
        "cdn_url": {
            "default": "https://{bucket}.{region}.cdn.digitaloceanspaces.com/{key}",
            "help": "S3 CDN url, {bucket}, {region} and {key} are inserted at runtime",
        },
        "private": {"default": False, "type": "bool", "help": "if true S3 files will not be readable online"},
    },
    "description": """
    S3Storage: A storage module for saving media files to an S3-compatible object storage.

    ### Features
    - Uploads media files to an S3 bucket with customizable configurations.
    - Supports `random_no_duplicate` mode to avoid duplicate uploads by checking existing files based on SHA-256 hashes.
    - Automatically generates unique paths for files when duplicates are found.
    - Configurable endpoint and CDN URL for different S3-compatible providers.
    - Supports both private and public file storage, with public files being readable online.

    ### Notes
    - Requires S3 credentials (API key and secret) and a bucket name to function.
    - The `random_no_duplicate` option ensures no duplicate uploads by leveraging hash-based folder structures.
    - Uses `boto3` for interaction with the S3 API.
    - Depends on the `HashEnricher` module for hash calculation.
    """,
}
