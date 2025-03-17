{
    "name": "Atlos Feeder Database Storage",
    "type": ["feeder", "database", "storage"],
    "entry_point": "atlos_feeder_db_storage::AtlosFeederDbStorage",
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
            "type": "str",
        },
    },
    "description": """
    A module that integrates with the Atlos API to fetch source material URLs for archival, uplaod extracted media,
    
    [Atlos](https://www.atlos.org/) is a visual investigation and archiving platform designed for investigative research, journalism, and open-source intelligence (OSINT). 
    It helps users organize, analyze, and store media from various sources, making it easier to track and investigate digital evidence.
    
    To get started create a new project and obtain an API token from the settings page. You can group event's into Atlos's 'incidents'.
    Here you can add 'source material' by URLn and the Atlos feeder will fetch these URLs for archival.
    
    You can use Atlos only as a 'feeder', however you can also implement the 'database' and 'storage' features to store the media files in Atlos which is recommended.
    The Auto Archiver will retain the Atlos ID for each item, ensuring that the media and database outputs are uplaoded back into the relevant media item.
    
    
    ### Features
    - Connects to the Atlos API to retrieve a list of source material URLs.
    - Iterates through the URLs from all source material items which are unprocessed, visible, and ready to archive.
    - If the storage option is selected, it will store the media files alongside the original source material item in Atlos.
    - Is the database option is selected it will output the results to the media item, as well as updating failure status with error details when archiving fails.
    - Skips Storege/ database upload for items without an Atlos ID - restricting that you must use the Atlos feeder so that it has the Atlos ID to store the results with.

    ### Notes
    - Requires an Atlos account with a project and a valid API token for authentication.
    - Ensures only unprocessed, visible, and ready-to-archive URLs are returned.
    - Feches any media items within an Atlos project, regardless of separation into incidents.
    """,
}
