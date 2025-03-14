{
    "name": "Thumbnail Enricher",
    "type": ["enricher"],
    "requires_setup": False,
    "dependencies": {"python": ["loguru", "ffmpeg"], "bin": ["ffmpeg"]},
    "configs": {
        "thumbnails_per_minute": {
            "default": 60,
            "type": "int",
            "help": "how many thumbnails to generate per minute of video, can be limited by max_thumbnails",
        },
        "max_thumbnails": {
            "default": 16,
            "type": "int",
            "help": "limit the number of thumbnails to generate per video, 0 means no limit",
        },
    },
    "description": """
    Generates thumbnails for video files to provide visual previews.

    ### Features
    - Processes video files and generates evenly distributed thumbnails.
    - Calculates the number of thumbnails based on video duration, `thumbnails_per_minute`, and `max_thumbnails`.
    - Distributes thumbnails equally across the video's duration and stores them as media objects.
    - Adds metadata for each thumbnail, including timestamps and IDs.

    ### Notes
    - Requires `ffmpeg` to be installed and accessible via the system's PATH.
    - Handles videos without pre-existing duration metadata by probing with `ffmpeg`.
    - Skips enrichment for non-video media files.
    """,
}
