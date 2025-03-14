import shutil
from typing import IO
import os
from loguru import logger

from auto_archiver.core import Media
from auto_archiver.core import Storage
from auto_archiver.core.consts import SetupError


class LocalStorage(Storage):
    def setup(self) -> None:
        if len(self.save_to) > 200:
            raise SetupError(
                "Your save_to path is too long, this will cause issues saving files on your computer. Please use a shorter path."
            )

    def get_cdn_url(self, media: Media) -> str:
        dest = media.key

        if self.save_absolute:
            dest = os.path.abspath(dest)
        return dest

    def set_key(self, media, url, metadata):
        # clarify we want to save the file to the save_to folder

        old_folder = metadata.get("folder", "")
        metadata.set_context("folder", os.path.join(self.save_to, metadata.get("folder", "")))
        super().set_key(media, url, metadata)
        # don't impact other storages that might want a different 'folder' set
        metadata.set_context("folder", old_folder)

    def upload(self, media: Media, **kwargs) -> bool:
        # override parent so that we can use shutil.copy2 and keep metadata
        dest = media.key

        os.makedirs(os.path.dirname(dest), exist_ok=True)
        logger.debug(f"[{self.__class__.__name__}] storing file {media.filename} with key {media.key} to {dest}")

        res = shutil.copy2(media.filename, dest)
        logger.info(res)
        return True

    # must be implemented even if unused
    def uploadf(self, file: IO[bytes], key: str, **kwargs: dict) -> bool:
        pass
