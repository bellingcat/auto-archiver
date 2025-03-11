{
    "name": "OpenTimestamps Enricher",
    "type": ["enricher"],
    "requires_setup": True,
    "dependencies": {
        "python": [
            "loguru",
            "opentimestamps",
            "slugify",
        ],
    },
    "configs": {
        "use_calendars": {
            "default": True,
            "help": "Whether to connect to OpenTimestamps calendar servers to create timestamps. If false, creates local timestamp proofs only.",
            "type": "bool"
        },
        "calendar_urls": {
            "default": [
                "https://alice.btc.calendar.opentimestamps.org",
                "https://bob.btc.calendar.opentimestamps.org",
                "https://finney.calendar.eternitywall.com"
            ],
            "help": "List of OpenTimestamps calendar servers to use for timestamping.",
            "type": "list"
        },
        "calendar_whitelist": {
            "default": [],
            "help": "Optional whitelist of calendar servers. If empty, all calendar servers are allowed.",
            "type": "list"
        },
        "verify_timestamps": {
            "default": True,
            "help": "Whether to verify timestamps after creating them.",
            "type": "bool"
        }
    },
    "description": """
    Creates OpenTimestamps proofs for archived files, providing blockchain-backed evidence of file existence at a specific time.

    ### Features
    - Creates cryptographic timestamp proofs that link files to the Bitcoin blockchain
    - Verifies existing timestamp proofs to confirm the time a file existed
    - Uses multiple calendar servers to ensure reliability and redundancy
    - Stores timestamp proofs alongside original files for future verification

    ### Notes
    - Can work offline to create timestamp proofs that can be upgraded later
    - Verification checks if timestamps have been confirmed in the Bitcoin blockchain
    - Should run after files have been archived and hashed
    """
}