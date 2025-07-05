{
    "name": "Timestamping Enricher",
    "type": ["enricher"],
    "requires_setup": True,
    "dependencies": {
        "python": ["loguru", "slugify", "cryptography", "rfc3161_client", "certifi"],
    },
    "configs": {
        "tsa_urls": {
            "default": [
                # See https://github.com/trailofbits/rfc3161-client/issues/46 for a list of valid TSAs
                # Full list of TSAs: https://gist.github.com/Manouchehri/fd754e402d98430243455713efada710
                    "http://timestamp.identrust.com",
                    "http://timestamp.ssl.trustwave.com",
                    "http://zeitstempel.dfn.de",
                    "http://ts.ssl.com",
                    # "http://tsa.izenpe.com", # self-signed
                    "http://tsa.lex-persona.com/tsa",
                    # "http://ca.signfiles.com/TSAServer.aspx", # self-signed
                    # "http://tsa.sinpe.fi.cr/tsaHttp/", # self-signed
                    # "http://tsa.cra.ge/signserver/tsa?workerName=qtsa", # self-signed
                    "http://tss.cnbs.gob.hn/TSS/HttpTspServer",
                    # "http://dss.nowina.lu/pki-factory/tsa/good-tsa",
                    # "https://freetsa.org/tsr", # self-signed
                ],
            "help": "List of RFC3161 Time Stamp Authorities to use, separate with commas if passed via the command line.",
        },
        "cert_authorities": {
            "default": None,
            "help": "Path to a file containing trusted Certificate Authorities (CAs) in PEM format. If empty, the default system authorities are used.",
            "type": "str",
        },
        "allow_selfsigned": {
            "default": False,
            "help": "Whether or not to allow and save self-signed Timestamping certificates. This allows for a greater range of timestamping servers to be used, \
but they are not trusted authorities",
            "type": "bool"
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
    """,
}
