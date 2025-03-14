{
    "name": "Media Metadata Enricher",
    "type": ["enricher"],
    "requires_setup": True,
    "dependencies": {"python": ["loguru"], "bin": ["exiftool"]},
    "description": """
    Extracts metadata information from files using ExifTool.

    ### Features
    - Uses ExifTool to extract detailed metadata from media files.
    - Processes file-specific data like camera settings, geolocation, timestamps, and other embedded metadata.
    - Adds extracted metadata to the corresponding `Media` object within the `Metadata`.

    ### Notes
    - Requires ExifTool to be installed and accessible via the system's PATH.
    - Skips enrichment for files where metadata extraction fails.
    """,
}
