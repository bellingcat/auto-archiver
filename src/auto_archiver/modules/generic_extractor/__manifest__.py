{
    'name': 'Generic Extractor',
    'version': '0.1.0',
    'author': 'Bellingcat',
    'type': ['extractor'],
    'entry_point': 'generic_extractor:GenericExtractor',
    'requires_setup': False,
    'depends': ['core'],
    'external_dependencies': {
        'python': ['yt_dlp', 'requests', 'loguru', 'slugify'],
    },
    'description': """
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
"""
}