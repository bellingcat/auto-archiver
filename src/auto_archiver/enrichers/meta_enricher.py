import os
from loguru import logger

from . import Enricher
from ..core import Metadata


class MetaEnricher(Enricher):
    """
    Adds metadata information about the archive operations, to be included at the end of all enrichments
    """
    name = "meta_enricher"


    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {
        }

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"calculating file sizes for {url=} ({len(to_enrich.media)} media files)")

        total_size = 0
        for i, m in enumerate(to_enrich.media):
            file_stats = os.stat(m.filename)
            to_enrich.media[i].set("bytes", file_stats.st_size)
            to_enrich.media[i].set("size", self.human_readable_bytes(file_stats.st_size))
            total_size += file_stats.st_size
        
        to_enrich.set("total_bytes", total_size)
        to_enrich.set("total_size", self.human_readable_bytes(total_size))
        

    def human_readable_bytes(self, size: int) -> str:
        # receives number of bytes and returns human readble size
        for unit in ["bytes", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
