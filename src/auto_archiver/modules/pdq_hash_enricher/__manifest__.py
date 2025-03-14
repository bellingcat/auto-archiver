{
    "name": "PDQ Hash Enricher",
    "type": ["enricher"],
    "requires_setup": False,
    "dependencies": {
        "python": ["loguru", "pdqhash", "numpy", "PIL"],
    },
    "description": """
    PDQ Hash Enricher for generating perceptual hashes of media files.

    ### Features
    - Calculates perceptual hashes for image files using the PDQ hashing algorithm.
    - Enables detection of duplicate or near-duplicate visual content.
    - Processes images stored in `Metadata` objects, adding computed hashes to the corresponding `Media` entries.
    - Skips non-image media or files unsuitable for hashing (e.g., corrupted or unsupported formats).

    ### Notes
    - Best used after enrichers like `thumbnail_enricher` or `screenshot_enricher` to ensure images are available.
    - Uses the `pdqhash` library to compute 256-bit perceptual hashes, which are stored as hexadecimal strings.
    """,
}
