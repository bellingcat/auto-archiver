from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
from typing import IO, Any
from media import Media
from metadata import Metadata
from steps.step import Step
from loguru import logger
import os, uuid
from slugify import slugify


@dataclass
class StorageV2(Step):
    name = "storage"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    # only for typing...
    def init(name: str, config: dict) -> StorageV2:
        return Step.init(name, config, StorageV2)

    def store(self, media: Media, item: Metadata) -> None:
        self.set_key(media, item)
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

    def set_key(self, media: Media, item: Metadata) -> None:
        """takes the media and optionally item info and generates a key"""
        if media.key is not None and len(media.key) > 0: return
        folder = item.get("folder", "")
        ext = os.path.splitext(media.filename)[1]
        # media.key = os.path.join(folder, f"{str(uuid.uuid4())}{ext}")
        media.key = os.path.join(folder, slugify(item.get_url()), f"{str(uuid.uuid4())}{ext}")
