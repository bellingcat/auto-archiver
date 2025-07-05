{
    "name": "Generic Extractor",
    "version": "0.1.0",
    "author": "Bellingcat",
    "type": ["extractor"],
    "requires_setup": False,
    "dependencies": {"python": ["yt_dlp", "requests", "loguru", "slugify"], "bin": ["ffmpeg"]},
    "description": """
This is the generic extractor used by auto-archiver, which uses `yt-dlp` under the hood.

This module is responsible for downloading and processing media content from platforms
supported by `yt-dlp`, such as YouTube, Facebook, and others. It provides functionality
for retrieving videos, subtitles, comments, and other metadata, and it integrates with
the broader archiving framework.

For a full list of video platforms supported by `yt-dlp`, see the
[official documentation](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

### Features
- Supports downloading videos and playlists.
- Retrieves metadata like titles, descriptions, upload dates, and durations.
- Downloads subtitles and comments when enabled.
- Configurable options for handling live streams, proxies, and more.
- Supports authentication of websites using the 'authentication' settings from your orchestration.

### Dropins
- For websites supported by `yt-dlp` that also contain posts in addition to videos
 (e.g. Facebook, Twitter, Bluesky), dropins can be created to extract post data and create 
 metadata objects. Some dropins are included in this generic_archiver by default, but
custom dropins can be created to handle additional websites and passed to the archiver
via the command line using the `--dropins` option (TODO!).

You can see all currently implemented dropins in [the source code](https://github.com/bellingcat/auto-archiver/tree/main/src/auto_archiver/modules/generic_extractor).

### Auto-Updates

The Generic Extractor will also automatically check for updates to `yt-dlp` (every 5 days by default).
This can be configured using the `ytdlp_update_interval` setting (or disabled by setting it to -1).
If you are having issues with the extractor, you can review the version of `yt-dlp` being used with `yt-dlp --version`.

""",
    "configs": {
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
            "help": "http/https/socks proxy to use for the webdriver, eg https://proxy-user:password@proxy-ip:port",
        },
        "proxy_on_failure_only": {
            "default": True,
            "help": "Applies only if a proxy is set. In that case if this setting is True, the extractor will only use the proxy if the initial request fails; if it is False, the extractor will always use the proxy.",
        },
        "end_means_success": {
            "default": True,
            "help": "if True, any archived content will mean a 'success', if False this extractor will not return a 'success' stage; this is useful for cases when the yt-dlp will archive a video but ignore other types of content like images or text only pages that the subsequent extractors can retrieve.",
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
        "bguils_po_token_method": {
            "default": "auto",
            "help": "Set up a Proof of origin token provider. This process has additional requirements. See [authentication](https://auto-archiver.readthedocs.io/en/latest/how_to/authentication_how_to.html) for more information.",
            "choices": ["auto", "script", "disabled"],
        },
        "extractor_args": {
            "default": {},
            "help": "Additional arguments to pass to the yt-dlp extractor. See https://github.com/yt-dlp/yt-dlp/blob/master/README.md#extractor-arguments.",
            "type": "json_loader",
        },
        "ytdlp_update_interval": {
            "default": 5,
            "help": "How often to check for yt-dlp updates (days). If positive, will check and update yt-dlp every [num] days. Set it to -1 to disable, or 0 to always update on every run.",
            "type": "int",
        },
        "ytdlp_args": {
            "default": "",
            "help": "Additional arguments to pass to yt-dlp, e.g. --no-check-certificate or --plugin-dirs.\
See yt-dlp documentation here for more information: https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file#general-options\
Note: this is not to be confused with 'extractor_args' which are specific to the extractor itself.",
            "type": "str",
        },
    },
}
