{
    "name": "Wayback Machine Enricher",
    "type": ["enricher", "archiver"],
    "requires_setup": True,
    "dependencies": {
        "python": ["loguru", "requests"],
    },
    "entry_point": "wayback_enricher::WaybackExtractorEnricher",
    "configs": {
        "timeout": {"default": 15, "help": "seconds to wait for successful archive confirmation from wayback, if more than this passes the result contains the job_id so the status can later be checked manually."},
        "if_not_archived_within": {"default": None, "help": "only tell wayback to archive if no archive is available before the number of seconds specified, use None to ignore this option. For more information: https://docs.google.com/document/d/1Nsv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA"},
        "key": {"default": None, "required": True, "help": "wayback API key. to get credentials visit https://archive.org/account/s3.php"},
        "secret": {"default": None, "required": True, "help": "wayback API secret. to get credentials visit https://archive.org/account/s3.php"},
        "proxy_http": {"default": None, "help": "http proxy to use for wayback requests, eg http://proxy-user:password@proxy-ip:port"},
        "proxy_https": {"default": None, "help": "https proxy to use for wayback requests, eg https://proxy-user:password@proxy-ip:port"},
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
    """
}
