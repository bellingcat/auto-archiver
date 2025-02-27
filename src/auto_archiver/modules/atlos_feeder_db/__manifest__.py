{
    "name": "Atlos Feeder Database",
    "type": ["feeder", "database"],
"entry_point": "atlos_feeder_db::AtlosFeederDb",
    "requires_setup": True,
    "dependencies": {
        "python": ["loguru", "requests"],
    },
    "configs": {
        "api_token": {
            "type": "str",
            "required": True,
            "help": "An Atlos API token. For more information, see https://docs.atlos.org/technical/api/",
        },
        "atlos_url": {
            "default": "https://platform.atlos.org",
            "help": "The URL of your Atlos instance (e.g., https://platform.atlos.org), without a trailing slash.",
            "type": "str"
        },
    },
    "description": """
    AtlosFeederDb: A feeder module that integrates with the Atlos API to fetch source material URLs for archival,
    along with a database option to output archival results.
    
    Feeder: A feeder module that integrates with the Atlos API to fetch source material URLs for archival.

    ### Features
    - Connects to the Atlos API to retrieve a list of source material URLs.
    - Filters source materials based on visibility, processing status, and metadata.
    - Converts filtered source materials into `Metadata` objects with the relevant `atlos_id` and URL.
    - Iterates through paginated results using a cursor for efficient API interaction.
    - Outputs archival results to the Atlos API for storage and tracking.
    - Updates failure status with error details when archiving fails.
    - Processes and formats metadata, including ISO formatting for datetime fields.
    - Skips processing for items without an Atlos ID.

    ### Notes
    - Requires an Atlos API endpoint and a valid API token for authentication.
    - Ensures only unprocessed, visible, and ready-to-archive URLs are returned.
    - Handles pagination transparently when retrieving data from the Atlos API.
    """
}
