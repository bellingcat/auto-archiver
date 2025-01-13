"""
Enrichers are modular components that enhance archived content by adding
context, metadata, or additional processing.

These add additional information to the context, such as screenshots, hashes, and metadata.
They are designed to work within the archiving pipeline, operating on `Metadata` objects after
the archiving step and before storage or formatting.

Enrichers are optional but highly useful for making the archived data more powerful.


"""
from .enricher import Enricher
from .screenshot_enricher import ScreenshotEnricher 
from .wayback_enricher import WaybackArchiverEnricher
from .hash_enricher import HashEnricher
from .thumbnail_enricher import ThumbnailEnricher
from .wacz_enricher import WaczArchiverEnricher
from .whisper_enricher import WhisperEnricher
from .pdq_hash_enricher import PdqHashEnricher
from .metadata_enricher import MetadataEnricher
from .meta_enricher import MetaEnricher
from .ssl_enricher import SSLEnricher
from .timestamping_enricher import TimestampingEnricher