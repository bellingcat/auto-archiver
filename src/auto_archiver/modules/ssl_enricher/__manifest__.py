{
    "name": "SSL Certificate Enricher",
    "type": ["enricher"],
    "requires_setup": False,
    "dependencies": {
        "python": ["loguru", "slugify"],
    },
    "entry_point": "ssl_enricher::SSLEnricher",
    "configs": {
        "skip_when_nothing_archived": {
            "default": True,
            "type": "bool",
            "help": "if true, will skip enriching when no media is archived",
        },
    },
    "description": """
    Retrieves SSL certificate information for a domain and stores it as a file.

    ### Features
    - Fetches SSL certificates for domains using the HTTPS protocol.
    - Stores certificates in PEM format and adds them as media to the metadata.
    - Skips enrichment if no media has been archived, based on the `skip_when_nothing_archived` configuration.

    ### Notes
    - Requires the target URL to use the HTTPS scheme; other schemes are not supported.
    """,
}
