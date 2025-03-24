"""Hash Enricher for generating cryptographic hashes of media files.

The `HashEnricher` calculates cryptographic hashes (e.g., SHA-256, SHA3-512)
for media files stored in `Metadata` objects. These hashes are used for
validating content integrity, ensuring data authenticity, and identifying
exact duplicates. The hash is computed by reading the file's bytes in chunks,
making it suitable for handling large files efficiently.

"""

import hashlib
from loguru import logger

from auto_archiver.core import Enricher
from auto_archiver.core import Metadata
from auto_archiver.utils.misc import calculate_file_hash


class HashEnricher(Enricher):
    """
    Calculates hashes for Media instances
    """

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"calculating media hashes for {url=} (using {self.algorithm})")

        for i, m in enumerate(to_enrich.media):
            if len(hd := self.calculate_hash(m.filename)):
                to_enrich.media[i].set("hash", f"{self.algorithm}:{hd}")

    def calculate_hash(self, filename) -> str:
        hash_algo = None
        if self.algorithm == "SHA-256":
            hash_algo = hashlib.sha256
        elif self.algorithm == "SHA3-512":
            hash_algo = hashlib.sha3_512
        else:
            return ""
        return calculate_file_hash(filename, hash_algo, self.chunksize)
