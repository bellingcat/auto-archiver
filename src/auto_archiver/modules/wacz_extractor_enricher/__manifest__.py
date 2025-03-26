{
    "name": "WACZ Enricher (and Extractor)",
    "type": ["enricher", "extractor"],
    "entry_point": "wacz_extractor_enricher::WaczExtractorEnricher",
    "requires_setup": True,
    "dependencies": {
        "python": ["loguru", "jsonlines", "warcio"],
        # TODO?
        "bin": ["docker"],
    },
    "configs": {
        "profile": {
            "default": None,
            "help": "browsertrix-profile (for profile generation see https://crawler.docs.browsertrix.com/user-guide/browser-profiles/).",
        },
        "docker_commands": {"default": None, "help": "if a custom docker invocation is needed"},
        "timeout": {"default": 120, "help": "timeout for WACZ generation in seconds", "type": "int"},
        "extract_media": {
            "default": False,
            "type": "bool",
            "help": "If enabled all the images/videos/audio present in the WACZ archive will be extracted into separate Media and appear in the html report. The .wacz file will be kept untouched.",
        },
        "extract_screenshot": {
            "default": True,
            "type": "bool",
            "help": "If enabled the screenshot captured by browsertrix will be extracted into separate Media and appear in the html report. The .wacz file will be kept untouched.",
        },
        "socks_proxy_host": {
            "default": None,
            "help": "SOCKS proxy host for browsertrix-crawler, use in combination with socks_proxy_port. eg: user:password@host",
        },
        "socks_proxy_port": {
            "default": None,
            "type": "int",
            "help": "SOCKS proxy port for browsertrix-crawler, use in combination with socks_proxy_host. eg 1234",
        },
        "proxy_server": {"default": None, "help": "SOCKS server proxy URL, in development"},
    },
    "description": """
    Creates .WACZ archives of web pages using the `browsertrix-crawler` tool, with options for media extraction and screenshot saving.
    [Browsertrix-crawler](https://crawler.docs.browsertrix.com/user-guide/) is a headless browser-based crawler that archives web pages in WACZ format.

    ## Features
    - Archives web pages into .WACZ format using Docker or direct invocation of `browsertrix-crawler`.
    - Supports custom profiles for archiving private or dynamic content.
    - Extracts media (images, videos, audio) and screenshots from the archive, optionally adding them to the enrichment pipeline.
    - Generates metadata from the archived page's content and structure (e.g., titles, text).

    ## Setup

    ### Using Docker
    If you are using the Auto Archiver [Docker image](https://auto-archiver.readthedocs.io/en/latest/installation/installation.html#installing-with-docker)
    to run Auto Archiver (recommended), then everything is set up and you can use WACZ out of the box!
    Otherwise, if you are using a local install of Auto Archiver (e.g. pip or dev install), then you will need to install Docker and run 
    the docker daemon to be able to run the `browsertrix-crawler` tool.

    ### Browsertrix Profiles
    A browsertrix profile is a custom browser profile (login information, browser extensions, etc.) that can be used to archive private or dynamic content.
    You can run the WACZ Enricher without a profile, but for more resilient archiving, it is recommended to create a profile.
    See the [Browsertrix documentation](https://crawler.docs.browsertrix.com/user-guide/browser-profiles/) for more information on how to use the `create-login-profile` tool.



    ### Docker in Docker
    If you are running Auto Archiver within a Docker container, you will need to enable Docker in Docker to run the `browsertrix-crawler` tool.
    This can be done by setting the `WACZ_ENABLE_DOCKER` environment variable to `1`.


    """,
}
