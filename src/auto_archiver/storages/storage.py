from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
from typing import IO

from ..core import Media, Step, ArchivingContext
from ..enrichers import HashEnricher
from loguru import logger
import os, uuid
from slugify import slugify


@dataclass
class Storage(Step):
    name = "storage"
    PATH_GENERATOR_OPTIONS = ["flat", "url", "random"]
    FILENAME_GENERATOR_CHOICES = ["random", "static"]

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        assert self.path_generator in Storage.PATH_GENERATOR_OPTIONS, f"path_generator must be one of {Storage.PATH_GENERATOR_OPTIONS}"
        assert self.filename_generator in Storage.FILENAME_GENERATOR_CHOICES, f"filename_generator must be one of {Storage.FILENAME_GENERATOR_CHOICES}"

    @staticmethod
    def configs() -> dict:
        return {
            "path_generator": {
                "default": "url",
                "help": "how to store the file in terms of directory structure: 'flat' sets to root; 'url' creates a directory based on the provided URL; 'random' creates a random directory.",
                "choices": Storage.PATH_GENERATOR_OPTIONS
            },
            "filename_generator": {
                "default": "random",
                "help": "how to name stored files: 'random' creates a random string; 'static' uses a replicable strategy such as a hash.",
                "choices": Storage.FILENAME_GENERATOR_CHOICES
            }
        }

    def init(name: str, config: dict) -> Storage:
        # only for typing...
        return Step.init(name, config, Storage)

    def store(self, media: Media, url: str) -> None:
        if media.is_stored(): 
            logger.debug(f"{media.key} already stored, skipping")
            return
        self.set_key(media, url)
        self.upload(media)
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

        # path_generator logic
        if self.path_generator == "flat":
            path = ""
            filename = slugify(filename)  # in case it comes with os.sep
        elif self.path_generator == "url": path = slugify(url)
        elif self.path_generator == "random":
            path = ArchivingContext.get("random_path", str(uuid.uuid4())[:16], True)

        # filename_generator logic
        if self.filename_generator == "random": filename = str(uuid.uuid4())[:16]
        elif self.filename_generator == "static":
            he = HashEnricher({"hash_enricher": {"algorithm": ArchivingContext.get("hash_enricher.algorithm"), "chunksize": 1.6e7}})
            hd = he.calculate_hash(media.filename)
            filename = hd[:24]

        media.key = os.path.join(folder, path, f"{filename}{ext}")
