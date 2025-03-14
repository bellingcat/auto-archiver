{
    "name": "Instagram API Extractor",
    "type": ["extractor"],
    "entry_point": "instagram_api_extractor::InstagramAPIExtractor",
    "dependencies": {
        "python": [
            "requests",
            "loguru",
            "retrying",
            "tqdm",
        ],
    },
    "requires_setup": True,
    "configs": {
        "access_token": {"default": None, "help": "a valid instagrapi-api token"},
        "api_endpoint": {"required": True, "help": "API endpoint to use"},
        "full_profile": {
            "default": False,
            "type": "bool",
            "help": "if true, will download all posts, tagged posts, stories, and highlights for a profile, if false, will only download the profile pic and information.",
        },
        "full_profile_max_posts": {
            "default": 0,
            "type": "int",
            "help": "Use to limit the number of posts to download when full_profile is true. 0 means no limit. limit is applied softly since posts are fetched in batch, once to: posts, tagged posts, and highlights",
        },
        "minimize_json_output": {
            "default": True,
            "type": "bool",
            "help": "if true, will remove empty values from the json output",
        },
    },
    "description": """
Archives various types of Instagram content using the Instagrapi API.

Requires setting up an Instagrapi API deployment and providing an access token and API endpoint.

### Features
- Connects to an Instagrapi API deployment to fetch Instagram profiles, posts, stories, highlights, reels, and tagged content.
- Supports advanced configuration options, including:
  - Full profile download (all posts, stories, highlights, and tagged content).
  - Limiting the number of posts to fetch for large profiles.
  - Minimising JSON output to remove empty fields and redundant data.
- Provides robust error handling and retries for API calls.
- Ensures efficient media scraping, including handling nested or carousel media items.
- Adds downloaded media and metadata to the result for further processing.

### Notes
- Requires a valid Instagrapi API token (`access_token`) and API endpoint (`api_endpoint`).
- Full-profile downloads can be limited by setting `full_profile_max_posts`.
- Designed to fetch content in batches for large profiles, minimising API load.
""",
}
