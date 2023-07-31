import traceback
import pdqhash
import numpy as np
from PIL import Image, UnidentifiedImageError
from loguru import logger

from . import Enricher
from ..core import Metadata


class PdqHashEnricher(Enricher):
    """
    Calculates perceptual hashes for Media instances using PDQ, allowing for (near-)duplicate detection.
    Ideally this enrichment is orchestrated to run after the thumbnail_enricher.
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
        logger.debug(f"calculating perceptual hashes for {url=}")
        media_with_hashes = []

        for m in to_enrich.media:
            for media in m.all_inner_media(True):
                media_id = media.get("id", "")
                if media.is_image() and "screenshot" not in media_id and "warc-file-" not in media_id and len(hd := self.calculate_pdq_hash(media.filename)):
                    media.set("pdq_hash", hd)
                    media_with_hashes.append(media.filename)

        logger.debug(f"calculated '{len(media_with_hashes)}' perceptual hashes for {url=}: {media_with_hashes}")

    def calculate_pdq_hash(self, filename):
        # returns a hexadecimal string with the perceptual hash for the given filename
        try:
            with Image.open(filename) as img:
                # convert the image to RGB
                image_rgb = np.array(img.convert("RGB"))
                # compute the 256-bit PDQ hash (we do not store the quality score)
                hash_array, _ = pdqhash.compute(image_rgb)
                hash = "".join(str(b) for b in hash_array)
                return hex(int(hash, 2))[2:]
        except UnidentifiedImageError as e:
            logger.error(f"Image {filename=} is likely corrupted or in unsupported format {e}: {traceback.format_exc()}")
        return ""
