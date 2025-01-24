{
    "name": "atlos_storage",
    "type": ["storage"],
    "requires_setup": True,
    "external_dependencies": {"python": ["loguru", "requests"], "bin": [""]},
    "configs": {
        "path_generator": {
            "default": "url",
            "help": "how to store the file in terms of directory structure: 'flat' sets to root; 'url' creates a directory based on the provided URL; 'random' creates a random directory.",
        },
        "filename_generator": {
            "default": "random",
            "help": "how to name stored files: 'random' creates a random string; 'static' uses a replicable strategy such as a hash.",
        },
        "api_token": {
            "default": None,
            "help": "An Atlos API token. For more information, see https://docs.atlos.org/technical/api/",
            "type": str,
        },
        "atlos_url": {
            "default": "https://platform.atlos.org",
            "help": "The URL of your Atlos instance (e.g., https://platform.atlos.org), without a trailing slash.",
            "type": str,
        },
    },
    "description": """
    AtlosStorage: A storage module for saving media files to the Atlos platform.

    ### Features
    - Uploads media files to Atlos using Atlos-specific APIs.
    - Automatically calculates SHA-256 hashes of media files for integrity verification.
    - Skips uploads for files that already exist on Atlos with the same hash.
    - Supports attaching metadata, such as `atlos_id`, to the uploaded files.
    - Provides CDN-like URLs for accessing uploaded media.

    ### Notes
    - Requires Atlos API configuration, including `atlos_url` and `api_token`.
    - Files are linked to an `atlos_id` in the metadata, ensuring proper association with Atlos source materials.
    """,
}
