{
    "name": "Atlos Feeder",
    "type": ["feeder"],
    "requires_setup": True,
    "external_dependencies": {
        "python": ["loguru", "requests"],
    },
    "configs": {
        "api_token": {
            "default": None,
            "help": "An Atlos API token. For more information, see https://docs.atlos.org/technical/api/",
            "type": str
        },
        "atlos_url": {
            "default": "https://platform.atlos.org",
            "help": "The URL of your Atlos instance (e.g., https://platform.atlos.org), without a trailing slash.",
            "type": str
        },
    },
    "description": """
    AtlosFeeder: A feeder module that integrates with the Atlos API to fetch source material URLs for archival.

    ### Features
    - Connects to the Atlos API to retrieve a list of source material URLs.
    - Filters source materials based on visibility, processing status, and metadata.
    - Converts filtered source materials into `Metadata` objects with the relevant `atlos_id` and URL.
    - Iterates through paginated results using a cursor for efficient API interaction.

    ### Notes
    - Requires an Atlos API endpoint and a valid API token for authentication.
    - Ensures only unprocessed, visible, and ready-to-archive URLs are returned.
    - Handles pagination transparently when retrieving data from the Atlos API.
    """
}
