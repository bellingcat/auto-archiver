{
    "name": "Atlos Storage",
    "type": ["storage"],
    "requires_setup": True,
    "dependencies": {
        "python": ["loguru", "boto3"],
        "bin": []
    },
    "description": """
    Stores media files in a [Atlos](https://www.atlos.org/).

    ### Features
    - Saves media files to Atlos, organizing them into folders based on the provided path structure.

    ### Notes
    - Requires setup with Atlos credentials.
    - Files are uploaded to the specified `root_folder_id` and organized by the `media.key` structure.
    """,
    "configs": {
        "api_token": {
            "default": None,
            "help": "An Atlos API token. For more information, see https://docs.atlos.org/technical/api/",
            "required": True,
            "type": "str"
        },
        "atlos_url": {
            "default": "https://platform.atlos.org",
            "help": "The URL of your Atlos instance (e.g., https://platform.atlos.org), without a trailing slash.",
            "type": "str"
        },
    }
}