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
        "calendar_urls": {
            "default": [
                "https://alice.btc.calendar.opentimestamps.org",
                "https://bob.btc.calendar.opentimestamps.org",
                "https://finney.calendar.eternitywall.com",
                # "https://ots.btc.catallaxy.com/", # ipv4 only
            ],
            "help": "List of OpenTimestamps calendar servers to use for timestamping. See here for a list of calendars maintained by opentimestamps:\
https://opentimestamps.org/#calendars",
            "type": "list",
        },
        "calendar_whitelist": {
            "default": [],
            "help": "Optional whitelist of calendar servers. Override this if you are using your own calendar servers. e.g. ['https://mycalendar.com']",
            "type": "list",
        },
    },
    "description": """
    Creates OpenTimestamps proofs for archived files, providing blockchain-backed evidence of file existence at a specific time.

    Uses OpenTimestamps – a service that timestamps data using the Bitcoin blockchain, providing a decentralized 
    and secure way to prove that data existed at a certain point in time. A SHA256 hash of the file to be timestamped is used as the token
    and sent to each of the 'timestamp calendars' for inclusion in the blockchain. The proof is then saved alongside the original file in a file with
    the '.ots' extension.

    ### Features
    - Creates cryptographic timestamp proofs that link files to the Bitcoin
    - Verifies timestamp proofs have been submitted to the blockchain (note: does not confirm they have been *added*)
    - Can use multiple calendar servers to ensure reliability and redundancy
    - Stores timestamp proofs alongside original files for future verification

    ### Timestamp status
    An opentimestamp, when submitted to a timestmap server will have a 'pending' status (Pending Attestation) as it waits to be added
    to the blockchain. Once it has been added to the blockchain, it will have a 'confirmed' status (Bitcoin Block Timestamp).
    This process typically takes several hours, depending on the calendar server and the current state of the Bitcoin network. As such,
    the status of all timestamps added will be 'pending' until they are subsequently confirmed (see 'Upgrading Timestamps' below).

    There are two possible statuses for a timestamp:
    - `Pending`: The timestamp has been submitted to the calendar server but has not yet been confirmed in the Bitcoin blockchain.
    - `Confirmed`: The timestamp has been confirmed in the Bitcoin blockchain.

    ### Upgrading Timestamps
    To upgrade a timestamp from 'pending' to 'confirmed', you can use the `ots upgrade` command from the opentimestamps-client package
    (install it with `pip install opentimesptamps-client`).
    Example: `ots upgrade my_file.ots`

    Here is a useful script that could be used to upgrade all timestamps in a directory, which could be run on a cron job:
```{code}  bash
find . -name "*.ots" -type f | while read file; do
    echo "Upgrading OTS $file"
    ots upgrade $file
done
# The result might look like:
# Upgrading OTS ./my_file.ots
# Got 1 attestation(s) from https://alice.btc.calendar.opentimestamps.org
# Success! Timestamp complete
```

```{note} Note: this will only upgrade the .ots files, and will not change the status text in any output .html files or any databases where the
metadata is stored (e.g. Google Sheets, CSV database, API database etc.).
```

    ### Verifying Timestamps
    The easiest way to verify a timestamp (ots) file is to install the opentimestamps-client command line tool and use the `ots verify` command.
    Example: `ots verify my_file.ots`

    ```{code}  bash
$ ots verify my_file.ots
Calendar https://bob.btc.calendar.opentimestamps.org: Pending confirmation in Bitcoin blockchain
Calendar https://finney.calendar.eternitywall.com: Pending confirmation in Bitcoin blockchain
Calendar https://alice.btc.calendar.opentimestamps.org: Timestamped by transaction 12345; waiting for 6 confirmations
```

    Note: if you're using a storage with `filename_generator` set to `static` or `random`, the files will be renamed when they are saved to the
    final location meaning you will need to specify the original filename when verifying the timestamp with `ots verify -f original_filename my_file.ots`.

    ### Choosing Calendar Servers

    By default, the OpenTimestamps enricher uses a set of public calendar servers provided by the 'opentimestamps' project.
    You can customize the list of calendar servers by providing URLs in the `calendar_urls` configuration option.

    ### Calendar WhiteList

    By default, the opentimestamps package only allows their own calendars to be used (see `DEFAULT_CALENDAR_WHITELIST` in `opentimestamps.calendar`),
    if you want to use your own calendars, then you can override this setting in the `calendar_whitelist` configuration option.

   
    """,
}
