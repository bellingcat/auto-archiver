from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
from typing import IO, Optional
import os

from auto_archiver.utils.misc import random_str

from auto_archiver.core import Media, Step, ArchivingContext, Metadata
from auto_archiver.modules.hash_enricher.hash_enricher import HashEnricher
from loguru import logger
from slugify import slugify


@dataclass
class Storage(Step):
    name = "storage"

    def init(name: str, config: dict) -> Storage:
        # only for typing...
        return Step.init(name, config, Storage)

    def store(self, media: Media, url: str, metadata: Optional[Metadata]=None) -> None:
        if media.is_stored(): 
            logger.debug(f"{media.key} already stored, skipping")
            return
        self.set_key(media, url)
        self.upload(media, metadata=metadata)
        media.add_url(self.get_cdn_url(media))

    @abstractmethod
    def get_cdn_url(self, media: Media) -> str: pass

    @abstractmethod
    def uploadf(self, file: IO[bytes], key: str, **kwargs: dict) -> bool: pass

    def upload(self, media: Media, **kwargs) -> bool:
        logger.debug(f'[{self.__class__.name}] storing file {media.filename} with key {media.key}')
        with open(media.filename, 'rb') as f:
            return self.uploadf(f, media, **kwargs)

    def set_key(self, media: Media, url) -> None:
        """takes the media and optionally item info and generates a key"""
        if media.key is not None and len(media.key) > 0: return
        folder = ArchivingContext.get("folder", "")
        filename, ext = os.path.splitext(media.filename)

        # Handle path_generator logic
        path_generator = ArchivingContext.get("path_generator", "url")
        if path_generator == "flat":
            path = ""
            filename = slugify(filename)  # Ensure filename is slugified
        elif path_generator == "url":
            path = slugify(url)
        elif path_generator == "random":
            path = ArchivingContext.get("random_path", random_str(24), True)
        else:
            raise ValueError(f"Invalid path_generator: {path_generator}")

        # Handle filename_generator logic
        filename_generator = ArchivingContext.get("filename_generator", "random")
        if filename_generator == "random":
            filename = random_str(24)
        elif filename_generator == "static":
            he = HashEnricher({"hash_enricher": {"algorithm": ArchivingContext.get("hash_enricher.algorithm"), "chunksize": 1.6e7}})
            hd = he.calculate_hash(media.filename)
            filename = hd[:24]
        else:
            raise ValueError(f"Invalid filename_generator: {filename_generator}")

        media.key = os.path.join(folder, path, f"{filename}{ext}")
