{
    "name": "Timestamping Enricher",
    "type": ["enricher"],
    "requires_setup": True,
    "external_dependencies": {
        "python": [
            "loguru",
            "slugify",
            "tsp_client",
            "asn1crypto",
            "certvalidator",
            "certifi"
        ],
    },
    "configs": {
        "tsa_urls": {
            "default": [
                "http://timestamp.digicert.com",
                "http://timestamp.identrust.com",
                "http://timestamp.globalsign.com/tsa/r6advanced1",
                "http://tss.accv.es:8318/tsa"
            ],
            "help": "List of RFC3161 Time Stamp Authorities to use, separate with commas if passed via the command line.",
            "type": lambda val: set(val.split(",")),
        }
    },
    "description": """
    Generates RFC3161-compliant timestamp tokens using Time Stamp Authorities (TSA) for archived files.

    ### Features
    - Creates timestamp tokens to prove the existence of files at a specific time, useful for legal and authenticity purposes.
    - Aggregates file hashes into a text file and timestamps the concatenated data.
    - Uses multiple Time Stamp Authorities (TSAs) to ensure reliability and redundancy.
    - Validates timestamping certificates against trusted Certificate Authorities (CAs) using the `certifi` trust store.

    ### Notes
    - Should be run after the `hash_enricher` to ensure file hashes are available.
    - Requires internet access to interact with the configured TSAs.
    """
}
