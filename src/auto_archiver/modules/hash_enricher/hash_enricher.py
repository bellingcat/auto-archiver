""" Hash Enricher for generating cryptographic hashes of media files.

The `HashEnricher` calculates cryptographic hashes (e.g., SHA-256, SHA3-512)
for media files stored in `Metadata` objects. These hashes are used for
validating content integrity, ensuring data authenticity, and identifying
exact duplicates. The hash is computed by reading the file's bytes in chunks,
making it suitable for handling large files efficiently.

"""
import hashlib
from loguru import logger

from auto_archiver.core import Enricher
from auto_archiver.core import Metadata, ArchivingContext


class HashEnricher(Enricher):
    """
    Calculates hashes for Media instances
    """

    def __init__(self, config: dict = None):
        """
        Initialize the HashEnricher with a configuration dictionary.
        """
        super().__init__()
        # TODO set these from the manifest?
        # Set default values
        self.algorithm = config.get("algorithm", "SHA-256") if config else "SHA-256"
        self.chunksize = config.get("chunksize", int(1.6e7)) if config else int(1.6e7)


    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"calculating media hashes for {url=} (using {self.algorithm})")

        for i, m in enumerate(to_enrich.media):
            if len(hd := self.calculate_hash(m.filename)):
                to_enrich.media[i].set("hash", f"{self.algorithm}:{hd}")

    def calculate_hash(self, filename) -> str:
        hash = None
        if self.algorithm == "SHA-256":
            hash = hashlib.sha256()
        elif self.algorithm == "SHA3-512":
            hash = hashlib.sha3_512()
        else: return ""
        with open(filename, "rb") as f:
            while True:
                buf = f.read(self.chunksize)
                if not buf: break
                hash.update(buf)
        return hash.hexdigest()
