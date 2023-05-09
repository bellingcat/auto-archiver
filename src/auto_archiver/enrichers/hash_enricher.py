import hashlib
from loguru import logger

from . import Enricher
from ..core import Metadata, ArchivingContext


class HashEnricher(Enricher):
    """
    Calculates hashes for Media instances
    """
    name = "hash_enricher"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        algo_choices = self.configs()["algorithm"]["choices"]
        assert self.algorithm in algo_choices, f"Invalid hash algorithm selected, must be one of {algo_choices} (you selected {self.algorithm})."
        self.chunksize = int(self.chunksize)
        ArchivingContext.set("hash_enricher.algorithm", self.algorithm, keep_on_reset=True)

    @staticmethod
    def configs() -> dict:
        return {
            "algorithm": {"default": "SHA-256", "help": "hash algorithm to use", "choices": ["SHA-256", "SHA3-512"]},
            "chunksize": {"default": 1.6e7, "help": "number of bytes to use when reading files in chunks (if this value is too large you will run out of RAM), default is 16MB"},
        }

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"calculating media hashes for {url=} (using {self.algorithm})")

        for i, m in enumerate(to_enrich.media):
            if len(hd := self.calculate_hash(m.filename)):
                to_enrich.media[i].set("hash", f"{self.algorithm}:{hd}")

    def calculate_hash(self, filename):
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
