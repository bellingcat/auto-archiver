{
    "name": "Wayback Machine Enricher (and Extractor)",
    "type": ["enricher", "extractor"],
    "entry_point": "wayback_extractor_enricher::WaybackExtractorEnricher",
    "requires_setup": True,
    "dependencies": {
        "python": ["loguru", "requests"],
    },
    "configs": {
        "timeout": {
            "default": 15,
            "type": "int",
            "help": "seconds to wait for successful archive confirmation from wayback, if more than this passes the result contains the job_id so the status can later be checked manually.",
        },
        "if_not_archived_within": {
            "default": None,
            "help": "only tell wayback to archive if no archive is available before the number of seconds specified, use None to ignore this option. For more information: https://docs.google.com/document/d/1Nsv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA",
        },
        "key": {
            "required": True,
            "help": "wayback API key. to get credentials visit https://archive.org/account/s3.php",
        },
        "secret": {
            "required": True,
            "help": "wayback API secret. to get credentials visit https://archive.org/account/s3.php",
        },
        "proxy_http": {
            "default": None,
            "help": "http proxy to use for wayback requests, eg http://proxy-user:password@proxy-ip:port",
        },
        "proxy_https": {
            "default": None,
            "help": "https proxy to use for wayback requests, eg https://proxy-user:password@proxy-ip:port",
        },
    },
    "description": """
    Submits the current URL to the Wayback Machine for archiving and returns either a job ID or the completed archive URL.

    ### Features
    - Archives URLs using the Internet Archive's Wayback Machine API.
    - Supports conditional archiving based on the existence of prior archives within a specified time range.
    - Provides proxies for HTTP and HTTPS requests.
    - Fetches and confirms the archive URL or provides a job ID for later status checks.

    ### Notes
    - Requires a valid Wayback Machine API key and secret.
    - Handles rate-limiting by Wayback Machine and retries status checks with exponential backoff.
    
    ### Steps to Get an Wayback API Key:
    - Sign up for an account at [Internet Archive](https://archive.org/account/signup).
    - Log in to your account.
    - Navigte to your [account settings](https://archive.org/account).
    - or: https://archive.org/developers/tutorial-get-ia-credentials.html
    - Under Wayback Machine API Keys, generate a new key.
    - Note down your API key and secret, as they will be required for authentication.
    """,
}
