{
    "name": "Ghost Archive Enricher",
    "type": ["enricher"],
    "entry_point": "ghostarchive_enricher::GhostarchiveEnricher",
    "requires_setup": False,
    "dependencies": {
        "python": ["loguru", "requests", "bs4", "seleniumbase"],
    },
    "configs": {
        "timeout": {
            "default": 120,
            "type": "int",
            "help": "seconds to wait for successful archive confirmation from Ghost Archive.",
        },
        "check_existing": {
            "default": True,
            "type": "bool",
            "help": "whether to search for an existing archive before submitting a new one.",
        },
        "proxy_http": {
            "default": None,
            "help": "http proxy to use for requests, eg http://proxy-user:password@proxy-ip:port",
        },
        "proxy_https": {
            "default": None,
            "help": "https proxy to use for requests, eg https://proxy-user:password@proxy-ip:port",
        },
    },
    "description": """
    Submits the current URL to [Ghost Archive](https://ghostarchive.org/) for archiving and returns the archived page URL.

    Used as an **enricher** to add a Ghost Archive URL to items already extracted by other modules.

    ### Features
    - Archives any public URL using the Ghost Archive service.
    - Optionally checks for existing archives before submitting a new one.
    - Supports HTTP and HTTPS proxies for requests.
    - Parses HTML responses to extract archive URLs (Ghost Archive has no JSON API).

    ### Important
    - This module confirms that Ghost Archive accepted the URL submission and returned an archive link.
      It does **not** verify the contents or completeness of the archived page.

    ### Notes
    - Ghost Archive is a free service with no authentication required.
    - Archived pages must be smaller than 50 MB (including CSS, fonts, images, etc.).
    - Videos are archived up to 360p and must be under 100 MB and shorter than 30 minutes.
    - Archival may take up to 5 minutes depending on the queue and page complexity.
    - Archived content is stored indefinitely.
    - Ghost Archive does not archive pages that require authentication or form submission.

    ### Limitations
    - No official API — this module interacts with the Ghost Archive web interface.
    - The submission endpoint is protected by Cloudflare, so a headless browser (SeleniumBase) is used for new submissions.
    - Searching for existing archives uses plain HTTP requests and does not require a browser.
    - Rate limiting may apply; consider using a delay between requests if archiving many URLs.
    """,
}
