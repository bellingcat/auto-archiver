{
    "name": "Auto Archiver API Database",
    "type": ["database"],
    "entry_point": "api_db::AAApiDb",
    "requires_setup": True,
    "dependencies": {
        "python": ["requests", "loguru"],
    },
    "configs": {
        "api_endpoint": {
            "required": True,
            "help": "API endpoint where calls are made to",
        },
        "api_token": {"default": None, "help": "API Bearer token."},
        "public": {
            "default": False,
            "type": "bool",
            "help": "whether the URL should be publicly available via the API",
        },
        "author_id": {"default": None, "help": "which email to assign as author"},
        "group_id": {
            "default": None,
            "help": "which group of users have access to the archive in case public=false as author",
        },
        "use_api_cache": {
            "default": False,
            "type": "bool",
            "help": "if True then the API database will be queried prior to any archiving operations and stop if the link has already been archived",
        },
        "store_results": {
            "default": True,
            "type": "bool",
            "help": "when set, will send the results to the API database.",
        },
        "tags": {
            "default": [],
            "help": "what tags to add to the archived URL",
        },
    },
    "description": """
     Provides integration with the Auto Archiver API for querying and storing archival data.

### Features
- **API Integration**: Supports querying for existing archives and submitting results.
- **Duplicate Prevention**: Avoids redundant archiving when `use_api_cache` is disabled.
- **Configurable**: Supports settings like API endpoint, authentication token, tags, and permissions.
- **Tagging and Metadata**: Adds tags and manages metadata for archives.
- **Optional Storage**: Archives results conditionally based on configuration.

### Setup
Requires access to an Auto Archiver API instance and a valid API token.
     """,
}
