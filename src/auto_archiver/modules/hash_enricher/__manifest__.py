{
    "name": "Hash Enricher",
    "type": ["enricher"],
    "requires_setup": False,
    "dependencies": {
        "python": ["loguru"],
    },
    "configs": {
        "algorithm": {"default": "SHA-256", "help": "hash algorithm to use", "choices": ["SHA-256", "SHA3-512"]},
        # TODO add non-negative requirement to match previous implementation?
        "chunksize": {
            "default": 16000000,
            "help": "number of bytes to use when reading files in chunks (if this value is too large you will run out of RAM), default is 16MB",
            "type": "int",
        },
    },
    "description": """
Generates cryptographic hashes for media files to ensure data integrity and authenticity.

### Features
- Calculates cryptographic hashes (SHA-256 or SHA3-512) for media files stored in `Metadata` objects.
- Ensures content authenticity, integrity validation, and duplicate identification.
- Efficiently processes large files by reading file bytes in configurable chunk sizes.
- Supports dynamic configuration of hash algorithms and chunk sizes.
- Updates media metadata with the computed hash value in the format `<algorithm>:<hash>`.

### Notes
- Default hash algorithm is SHA-256, but SHA3-512 is also supported.
- Chunk size defaults to 16 MB but can be adjusted based on memory requirements.
- Useful for workflows requiring hash-based content validation or deduplication.
""",
}
