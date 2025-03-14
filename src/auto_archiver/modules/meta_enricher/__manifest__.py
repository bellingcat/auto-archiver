{
    "name": "Archive Metadata Enricher",
    "type": ["enricher"],
    "requires_setup": False,
    "dependencies": {
        "python": ["loguru"],
    },
    "description": """ 
    Adds metadata information about the archive operations, Adds metadata about archive operations, including file sizes and archive duration./
    To be included at the end of all enrichments.
    
    ### Features
- Calculates the total size of all archived media files, storing the result in human-readable and byte formats.
- Computes the duration of the archival process, storing the elapsed time in seconds.
- Ensures all enrichments are performed only if the `Metadata` object contains valid data.
- Adds detailed metadata to provide insights into file sizes and archival performance.

### Notes
- Skips enrichment if no media or metadata is available in the `Metadata` object.
- File sizes are calculated using the `os.stat` module, ensuring accurate byte-level reporting.
""",
}
