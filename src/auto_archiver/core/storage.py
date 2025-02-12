"""
Base module for Storage modules – modular components that store media objects in various locations.
"""

from __future__ import annotations
from abc import abstractmethod
from typing import IO
import os

from loguru import logger
from slugify import slugify

from auto_archiver.utils.misc import random_str

from auto_archiver.core import Media, BaseModule, Metadata
from auto_archiver.modules.hash_enricher.hash_enricher import HashEnricher
from auto_archiver.core.module import get_module
class Storage(BaseModule):
    
    """
    Base class for implementing storage modules in the media archiving framework.

    Subclasses must implement the `get_cdn_url` and `uploadf` methods to define their behavior.
    """

    def store(self, media: Media, url: str, metadata: Metadata=None) -> None:
        if media.is_stored(in_storage=self): 
            logger.debug(f"{media.key} already stored, skipping")
            return
        self.set_key(media, url, metadata)
        self.upload(media, metadata=metadata)
        media.add_url(self.get_cdn_url(media))

    @abstractmethod
    def get_cdn_url(self, media: Media) -> str:
        """
        Returns the URL of the media object stored in the CDN.
        """
        pass

    @abstractmethod
    def uploadf(self, file: IO[bytes], key: str, **kwargs: dict) -> bool:
        """
        Uploads (or saves) a file to the storage service/location.
        """
        pass

    def upload(self, media: Media, **kwargs) -> bool:
        logger.debug(f'[{self.__class__.__name__}] storing file {media.filename} with key {media.key}')
        with open(media.filename, 'rb') as f:
            return self.uploadf(f, media, **kwargs)

    def set_key(self, media: Media, url, metadata: Metadata) -> None:
        """takes the media and optionally item info and generates a key"""
        if media.key is not None and len(media.key) > 0: return
        folder = metadata.get_context('folder', '')
        filename, ext = os.path.splitext(media.filename)

        # Handle path_generator logic
        path_generator = self.config.get("path_generator", "url")
        if path_generator == "flat":
            path = ""
            filename = slugify(filename)  # Ensure filename is slugified
        elif path_generator == "url":
            path = slugify(url)
        elif path_generator == "random":
            path = self.config.get("random_path", random_str(24), True)
        else:
            raise ValueError(f"Invalid path_generator: {path_generator}")

        # Handle filename_generator logic
        filename_generator = self.config.get("filename_generator", "random")
        if filename_generator == "random":
            filename = random_str(24)
        elif filename_generator == "static":
            # load the hash_enricher module
            he = get_module(HashEnricher, self.config)
            hd = he.calculate_hash(media.filename)
            filename = hd[:24]
        else:
            raise ValueError(f"Invalid filename_generator: {filename_generator}")

        media.key = os.path.join(folder, path, f"{filename}{ext}")
