import subprocess
import traceback
from loguru import logger

from . import Enricher
from ..core import Metadata


class MetadataEnricher(Enricher):
    """
    Extracts metadata information from files using exiftool.
    """
    name = "metadata_enricher"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {}

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"extracting EXIF metadata for {url=}")

        for i, m in enumerate(to_enrich.media):
            if len(md := self.get_metadata(m.filename)):
                to_enrich.media[i].set("metadata", md)

    def get_metadata(self, filename: str) -> dict:
        try:
            # Run ExifTool command to extract metadata from the file
            cmd = ['exiftool', filename]
            result = subprocess.run(cmd, capture_output=True, text=True)

            # Process the output to extract individual metadata fields
            metadata = {}
            for line in result.stdout.splitlines():
                field, value = line.strip().split(':', 1)
                metadata[field.strip()] = value.strip()
            return metadata
        except FileNotFoundError:
            logger.error("[exif_enricher] ExifTool not found. Make sure ExifTool is installed and added to PATH.")
        except Exception as e:
            logger.error(f"Error occurred: {e}: {traceback.format_exc()}")
        return {}
