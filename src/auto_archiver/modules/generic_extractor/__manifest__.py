{
    "name": "Generic Extractor",
    "version": "0.1.0",
    "author": "Bellingcat",
    "type": ["extractor"],
    "requires_setup": False,
    "dependencies": {
        "python": ["yt_dlp", "requests", "loguru", "slugify"],
    },
    "description": """
This is the generic extractor used by auto-archiver, which uses `yt-dlp` under the hood.

This module is responsible for downloading and processing media content from platforms
supported by `yt-dlp`, such as YouTube, Facebook, and others. It provides functionality
for retrieving videos, subtitles, comments, and other metadata, and it integrates with
the broader archiving framework.

### Features
- Supports downloading videos and playlists.
- Retrieves metadata like titles, descriptions, upload dates, and durations.
- Downloads subtitles and comments when enabled.
- Configurable options for handling live streams, proxies, and more.

### Dropins
- For websites supported by `yt-dlp` that also contain posts in addition to videos
 (e.g. Facebook, Twitter, Bluesky), dropins can be created to extract post data and create 
 metadata objects. Some dropins are included in this generic_archiver by default, but
custom dropins can be created to handle additional websites and passed to the archiver
via the command line using the `--dropins` option (TODO!).
""",
    "configs": {
        "facebook_cookie": {
            "default": None,
            "help": "optional facebook cookie to have more access to content, from browser, looks like 'cookie: datr= xxxx'",
        },
        "subtitles": {"default": True, "help": "download subtitles if available", "type": "bool"},
        "comments": {
            "default": False,
            "help": "download all comments if available, may lead to large metadata",
            "type": "bool",
        },
        "livestreams": {
            "default": False,
            "help": "if set, will download live streams, otherwise will skip them; see --max-filesize for more control",
            "type": "bool",
        },
        "live_from_start": {
            "default": False,
            "help": "if set, will download live streams from their earliest available moment, otherwise starts now.",
            "type": "bool",
        },
        "proxy": {
            "default": "",
            "help": "http/socks (https seems to not work atm) proxy to use for the webdriver, eg https://proxy-user:password@proxy-ip:port",
        },
        "end_means_success": {
            "default": True,
            "help": "if True, any archived content will mean a 'success', if False this archiver will not return a 'success' stage; this is useful for cases when the yt-dlp will archive a video but ignore other types of content like images or text only pages that the subsequent archivers can retrieve.",
            "type": "bool",
        },
        "allow_playlist": {
            "default": False,
            "help": "If True will also download playlists, set to False if the expectation is to download a single video.",
            "type": "bool",
        },
        "max_downloads": {
            "default": "inf",
            "help": "Use to limit the number of videos to download when a channel or long page is being extracted. 'inf' means no limit.",
        },
        "cookies_from_browser": {
            "default": None,
            "type": "str",
            "help": "optional browser for ytdl to extract cookies from, can be one of: brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale",
        },
        "cookie_file": {
            "default": None,
            "help": "optional cookie file to use for Youtube, see instructions here on how to export from your browser: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp",
        },
    },
}
