{
    "name": "OpenTimestamps Enricher",
    "type": ["enricher"],
    "requires_setup": True,
    "dependencies": {
        "python": [
            "loguru",
            "opentimestamps",
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
                "https://finney.calendar.eternitywall.com",
                # "https://ots.btc.catallaxy.com/", # ipv4 only
            ],
            "help": "List of OpenTimestamps calendar servers to use for timestamping. See here for a list of calendars maintained by opentimestamps:\
https://opentimestamps.org/#calendars",
            "type": "list"
        },
        "calendar_whitelist": {
            "default": [],
            "help": "Optional whitelist of calendar servers. Override this if you are using your own calendar servers. e.g. ['https://mycalendar.com']",
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

    Uses OpenTimestamps – a service that timestamps data using the Bitcoin blockchain, providing a decentralized 
    and secure way to prove that data existed at a certain point in time.

    ### Features
    - Creates cryptographic timestamp proofs that link files to the Bitcoin blockchain
    - Verifies existing timestamp proofs to confirm the time a file existed
    - Uses multiple calendar servers to ensure reliability and redundancy
    - Stores timestamp proofs alongside original files for future verification

    ### Notes
    - Can work offline to create timestamp proofs that can be upgraded later
    - Verification checks if timestamps have been confirmed in the Bitcoin blockchain
    - Should run after files have been archived and hashed

    ### Verifying Timestamps Later
    If you wish to verify a timestamp (ots) file later, you can install the opentimestamps-client command line tool and use the `ots verify` command.
    Example: `ots verify my_file.ots`

    Note: if you're using local storage with a filename_generator set to 'static' (a hash) or random, the files will be renamed when they are saved to the
    final location meaning you will need to specify the original filename when verifying the timestamp with `ots verify -f original_filename my_file.ots`.
    """
}