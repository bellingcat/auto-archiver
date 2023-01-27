import hashlib
from loguru import logger

from . import Enricher
from ..core import Metadata


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

    @staticmethod
    def configs() -> dict:
        return {
            "algorithm": {"default": "SHA-256", "help": "hash algorithm to use", "choices": ["SHA-256", "SHA3-512"]}
        }

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"calculating media hashes for {url=} (using {self.algorithm})")

        for i, m in enumerate(to_enrich.media):
            with open(m.filename, "rb") as f:
                bytes = f.read()  # read entire file as bytes
                hash = None
                if self.algorithm == "SHA-256":
                    hash = hashlib.sha256(bytes)
                elif self.algorithm == "SHA3-512":
                    hash = hashlib.sha3_512(bytes)
                else: continue
                to_enrich.media[i].set("hash", f"{self.algorithm}:{hash.hexdigest()}")
