import datetime
import os
from loguru import logger

from auto_archiver.core import Enricher
from auto_archiver.core import Metadata


class MetaEnricher(Enricher):
    """
    Adds metadata information about the archive operations, to be included at the end of all enrichments
    """

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        if to_enrich.is_empty():
            logger.debug(f"[SKIP] META_ENRICHER there is no media or metadata to enrich: {url=}")
            return

        logger.debug(f"calculating archive metadata information for {url=}")

        self.enrich_file_sizes(to_enrich)
        self.enrich_archive_duration(to_enrich)

    def enrich_file_sizes(self, to_enrich: Metadata):
        logger.debug(
            f"calculating archive file sizes for url={to_enrich.get_url()} ({len(to_enrich.media)} media files)"
        )
        total_size = 0
        for media in to_enrich.get_all_media():
            file_stats = os.stat(media.filename)
            media.set("bytes", file_stats.st_size)
            media.set("size", self.human_readable_bytes(file_stats.st_size))
            total_size += file_stats.st_size

        to_enrich.set("total_bytes", total_size)
        to_enrich.set("total_size", self.human_readable_bytes(total_size))

    def human_readable_bytes(self, size: int) -> str:
        # receives number of bytes and returns human readble size
        for unit in ["bytes", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024

    def enrich_archive_duration(self, to_enrich):
        logger.debug(f"calculating archive duration for url={to_enrich.get_url()} ")

        archive_duration = datetime.datetime.now(datetime.timezone.utc) - to_enrich.get("_processed_at")
        to_enrich.set("archive_duration_seconds", archive_duration.seconds)
