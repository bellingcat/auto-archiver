from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
from typing import IO, Any
from media import Media
from metadata import Metadata
from steps.step import Step
from loguru import logger
import os, uuid


@dataclass
class StorageV2(Step):
    name = "storage"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    # only for typing...
    def init(name: str, config: dict) -> StorageV2:
        return Step.init(name, config, StorageV2)

    def store(self, media: Media, item: Metadata) -> Media:
        media = self.set_key(media, item)
        self.upload(media)
        media.cdn_url = self.get_cdn_url(media)
        return media

    @abstractmethod
    def uploadf(self, file: IO[bytes], key: str, **kwargs: dict) -> Any: pass

    def upload(self, media: Media, **kwargs) -> Any:
        logger.debug(f'[{self.__class__.name}] uploading file {media.filename} with key {media.key}')
        with open(media.filename, 'rb') as f:
            return self.uploadf(f, media, **kwargs)

    def set_key(self, media: Media, item: Metadata) -> Media:
        """takes the media and optionally item info and generates a key"""
        folder = item.get("folder", "")
        ext = os.path.splitext(media.filename)[1]
        media.key = os.path.join(folder, f"{str(uuid.uuid4())}{ext}")
        return media
