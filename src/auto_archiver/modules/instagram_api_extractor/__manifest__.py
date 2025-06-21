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
            "help": "Use to limit the number of posts to download when full_profile is true or when a URL for multiple posts is passed (like /stories /highlights ...). 0 means no limit. when full_profile is true the order of downloaded content is stories -> posts -> tagged posts -> highlights, so a value of 10 could download 2 stories, 7 posts, 1 tagged posts, and 0 highlights.",
        },
        "minimize_json_output": {
            "default": True,
            "type": "bool",
            "help": "if true, will remove empty values from the json output",
        },
    },
    "description": """
Archives Instagram content using a deployment of the [Instagrapi API](https://subzeroid.github.io/instagrapi/).

Requires either getting a token from using a hosted [(paid) service](https://api.instagrapi.com/docs) and setting this in the configuration file.
Alternatively you can run your own server. We have a basic script which you can use for this which can be ran locally or using Docker.
For more information, read the [how to guide](https://auto-archiver.readthedocs.io/en/latest/how_to/run_instagrapi_server.html) on this.

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
