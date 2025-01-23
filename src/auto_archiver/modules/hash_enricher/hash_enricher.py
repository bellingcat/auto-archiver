""" Hash Enricher for generating cryptographic hashes of media files.

The `HashEnricher` calculates cryptographic hashes (e.g., SHA-256, SHA3-512)
for media files stored in `Metadata` objects. These hashes are used for
validating content integrity, ensuring data authenticity, and identifying
exact duplicates. The hash is computed by reading the file's bytes in chunks,
making it suitable for handling large files efficiently.

"""
import hashlib
from loguru import logger

from auto_archiver.base_modules import Enricher
from auto_archiver.core import Metadata, ArchivingContext


class HashEnricher(Enricher):
    """
    Calculates hashes for Media instances
    """
    name = "hash_enricher"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        algos = self.configs()["algorithm"]
        algo_choices = algos["choices"]
        if not getattr(self, 'algorithm', None):
            if not config.get('algorithm'):
                logger.warning(f"No hash algorithm selected, defaulting to {algos['default']}")
                self.algorithm = algos["default"]
            else:
                self.algorithm = config["algorithm"]

        assert self.algorithm in algo_choices, f"Invalid hash algorithm selected, must be one of {algo_choices} (you selected {self.algorithm})."

        if not getattr(self, 'chunksize', None):
            if config.get('chunksize'):
                self.chunksize = config["chunksize"]
            else:
                self.chunksize = self.configs()["chunksize"]["default"]

        try:
            self.chunksize = int(self.chunksize)
        except ValueError:
            raise ValueError(f"Invalid chunksize value: {self.chunksize}. Must be an integer.")

        assert self.chunksize >= -1, "read length must be non-negative or -1"

        ArchivingContext.set("hash_enricher.algorithm", self.algorithm, keep_on_reset=True)

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
