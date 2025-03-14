{
    "name": "Twitter API Extractor",
    "type": ["extractor"],
    "requires_setup": True,
    "dependencies": {
        "python": [
            "requests",
            "loguru",
            "pytwitter",
            "slugify",
        ],
        "bin": [""],
    },
    "configs": {
        "bearer_token": {
            "default": None,
            "help": "[deprecated: see bearer_tokens] twitter API bearer_token which is enough for archiving, if not provided you will need consumer_key, consumer_secret, access_token, access_secret",
        },
        "bearer_tokens": {
            "default": [],
            "help": " a list of twitter API bearer_token which is enough for archiving, if not provided you will need consumer_key, consumer_secret, access_token, access_secret, if provided you can still add those for better rate limits. CSV of bearer tokens if provided via the command line",
        },
        "consumer_key": {"default": None, "help": "twitter API consumer_key"},
        "consumer_secret": {"default": None, "help": "twitter API consumer_secret"},
        "access_token": {"default": None, "help": "twitter API access_token"},
        "access_secret": {"default": None, "help": "twitter API access_secret"},
    },
    "description": """
        The `TwitterApiExtractor` fetches tweets and associated media using the Twitter API. 
        It supports multiple API configurations for extended rate limits and reliable access. 
        Features include URL expansion, media downloads (e.g., images, videos), and structured output 
        via `Metadata` and `Media` objects. Requires Twitter API credentials such as bearer tokens 
        or consumer key/secret and access token/secret.
        
        ### Features
        - Fetches tweets and their metadata, including text, creation timestamp, and author information.
        - Downloads media attachments (e.g., images, videos) in high quality.
        - Supports multiple API configurations for improved rate limiting.
        - Expands shortened URLs (e.g., `t.co` links).
        - Outputs structured metadata and media using `Metadata` and `Media` objects.
        
        ### Setup
        To use the `TwitterApiExtractor`, you must provide valid Twitter API credentials via configuration:
        - **Bearer Token(s)**: A single token or a list for rate-limited API access.
        - **Consumer Key and Secret**: Required for user-authenticated API access.
        - **Access Token and Secret**: Complements the consumer key for enhanced API capabilities.
        
        Credentials can be obtained by creating a Twitter developer account at [Twitter Developer Platform](https://developer.twitter.com/en).
        """,
}
