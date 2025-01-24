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
                    # [Adobe Approved Trust List] and [Windows Cert Store]
                    "http://timestamp.digicert.com",
                    "http://timestamp.identrust.com",
                    # "https://timestamp.entrust.net/TSS/RFC3161sha2TS", # not valid for timestamping
                    # "https://timestamp.sectigo.com", # wait 15 seconds between each request.

                    # [Adobe: European Union Trusted Lists].
                    # "https://timestamp.sectigo.com/qualified", # wait 15 seconds between each request.

                    # [Windows Cert Store]
                    "http://timestamp.globalsign.com/tsa/r6advanced1",
                    # [Adobe: European Union Trusted Lists] and [Windows Cert Store]
                    # "http://ts.quovadisglobal.com/eu", # not valid for timestamping
                    # "http://tsa.belgium.be/connect", # self-signed certificate in certificate chain
                    # "https://timestamp.aped.gov.gr/qtss", # self-signed certificate in certificate chain
                    # "http://tsa.sep.bg", # self-signed certificate in certificate chain
                    # "http://tsa.izenpe.com", #unable to get local issuer certificate
                    # "http://kstamp.keynectis.com/KSign", # unable to get local issuer certificate
                    "http://tss.accv.es:8318/tsa",
                ],
            "help": "List of RFC3161 Time Stamp Authorities to use, separate with commas if passed via the command line.",
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
