"""
Base module for Storage modules – modular components that store media objects in various locations.

If you are looking to implement a new storage module, you should subclass the `Storage` class and
implement the `get_cdn_url` and `uploadf` methods.

Your module **must** also have two config variables 'path_generator' and 'filename_generator' which
determine how the key is generated for the media object. The 'path_generator' and 'filename_generator'
variables can be set to one of the following values:
- 'flat': A flat structure with no subfolders
- 'url': A structure based on the URL of the media object
- 'random': A random structure

The 'filename_generator' variable can be set to one of the following values:
- 'random': A random string
- 'static': A replicable strategy such as a hash

If you don't want to use this naming convention, you can override the `set_key` method in your subclass.

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


class Storage(BaseModule):
    """
    Base class for implementing storage modules in the media archiving framework.

    Subclasses must implement the `get_cdn_url` and `uploadf` methods to define their behavior.
    """

    def store(self, media: Media, url: str, metadata: Metadata = None) -> None:
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

        This method should not be called directly, but instead through the 'store' method,
        which sets up the media for storage.
        """
        pass

    def upload(self, media: Media, **kwargs) -> bool:
        """
        Uploads a media object to the storage service.

        This method should not be called directly, but instead be called through the 'store' method,
        which sets up the media for storage.
        """
        logger.debug(f"[{self.__class__.__name__}] storing file {media.filename} with key {media.key}")
        with open(media.filename, "rb") as f:
            return self.uploadf(f, media, **kwargs)

    def set_key(self, media: Media, url: str, metadata: Metadata) -> None:
        """takes the media and optionally item info and generates a key"""

        if media.key is not None and len(media.key) > 0:
            # media key is already set
            return

        folder = metadata.get_context("folder", "")
        filename, ext = os.path.splitext(media.filename)

        # Handle path_generator logic
        path_generator = self.path_generator
        if path_generator == "flat":
            path = ""
        elif path_generator == "url":
            path = slugify(url)[:70]
        elif path_generator == "random":
            path = random_str(24)
        else:
            raise ValueError(f"Invalid path_generator: {path_generator}")

        # Handle filename_generator logic
        filename_generator = self.filename_generator
        if filename_generator == "random":
            filename = random_str(24)
        elif filename_generator == "static":
            # load the hash_enricher module
            he: HashEnricher = self.module_factory.get_module("hash_enricher", self.config)
            hd = he.calculate_hash(media.filename)
            filename = hd[:24]
        else:
            raise ValueError(f"Invalid filename_generator: {filename_generator}")

        key = os.path.join(folder, path, f"{filename}{ext}")
        media._key = key
