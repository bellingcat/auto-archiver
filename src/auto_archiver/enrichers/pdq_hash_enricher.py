import pdqhash
import numpy as np
from PIL import Image
from loguru import logger

from . import Enricher
from ..core import Metadata


class PdqHashEnricher(Enricher):
    """
    Calculates perceptual hashes for Media instances using PDQ, allowing for (near-)duplicate detection
    """
    name = "pdq_hash_enricher"

    def __init__(self, config: dict) -> None:
        # Without this STEP.__init__ is not called
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {}

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"calculating media hashes for {url=}")

        for i, m in enumerate(to_enrich.media):
            # only run for images and video thumbnails, not screenshots
            if m.filename.endswith(('.jpg', '.png', '.jpeg')) and m.key != "screenshot":
                if len(hd := self.calculate_pdq_hash(m.filename)):
                    to_enrich.media[i].set("pdq_hash", hd)

    def calculate_pdq_hash(self, filename):
        # open the image file
        with Image.open(filename) as img:
            # convert the image to RGB
            image_rgb = np.array(img.convert("RGB"))
            # compute the 256-bit PDQ hash (we do not store the quality score)
            hash, _ = pdqhash.compute(image_rgb)
            return hash
