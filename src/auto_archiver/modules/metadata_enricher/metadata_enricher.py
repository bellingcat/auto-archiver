import subprocess
import traceback
from auto_archiver.utils.custom_logger import logger

from auto_archiver.core import Enricher
from auto_archiver.core import Metadata


class MetadataEnricher(Enricher):
    """
    Extracts metadata information from files using exiftool.
    """

    def enrich(self, to_enrich: Metadata) -> None:
        logger.debug("Extracting EXIF metadata")

        for i, m in enumerate(to_enrich.media):
            if len(md := self.get_metadata(m.filename)):
                if self.look_for_keys != []:
                    md = self.select_metadata(md, self.look_for_keys)
                to_enrich.media[i].set("metadata", md)

    def get_metadata(self, filename: str) -> dict:
        try:
            # Run ExifTool command to extract metadata from the file
            cmd = ["exiftool", filename]
            result = subprocess.run(cmd, capture_output=True, text=True)
            # Process the output to extract individual metadata fields
            metadata = {}
            for line in result.stdout.splitlines():
                field, value = line.strip().split(":", 1)
                metadata[field.strip()] = value.strip()
            return metadata
        except FileNotFoundError as e:
            logger.error(f"ExifTool not found. Make sure ExifTool is installed and added to PATH. {e}")
        except Exception as e:
            logger.error(f"Error occurred: {e}: {traceback.format_exc()}")
        return {}

    def select_metadata(self, all_md, requested_metadata_keys):
        """
        coordinates the selection of metadata from the general exiftool output to the user-specified grocery list
        """
        # defining the batches of metadata that get pulled for special terms
        author_key_terms = ["author", "producer", "creator"]
        datetime_key_terms = ["date", "time"]
        location_key_terms = ["gps", "latitude", "longitude"]

        specified_md = {}
        for md_key in all_md.keys():
            md_key_lower = md_key.lower()
            # checking for special baskets within the grocery list of requested metadata
            if ("author" in requested_metadata_keys) and any(
                term in md_key_lower and len(all_md[md_key]) for term in author_key_terms
            ):
                specified_md[md_key] = all_md[md_key]
            if ("datetime" in requested_metadata_keys) and any(
                term in md_key_lower and len(all_md[md_key]) for term in datetime_key_terms
            ):
                specified_md[md_key] = all_md[md_key]
            if ("location" in requested_metadata_keys) and any(
                term in md_key_lower and len(all_md[md_key]) for term in location_key_terms
            ):
                specified_md[md_key] = all_md[md_key]
            # if the metadata value is requested directly
            if md_key_lower in requested_metadata_keys or md_key in requested_metadata_keys and len(all_md[md_key]):
                specified_md[md_key] = all_md[md_key]
        return specified_md
