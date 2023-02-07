
import shutil
from typing import IO
import os
from loguru import logger

from ..core import Media
from ..storages import Storage


class LocalStorage(Storage):
    name = "local_storage"

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        os.makedirs(self.save_to, exist_ok=True)

    @staticmethod
    def configs() -> dict:
        return dict(
            Storage.configs(),
            ** {
                "save_to": {"default": "./archived", "help": "folder where to save archived content"},
                "save_absolute": {"default": False, "help": "whether the path to the stored file is absolute or relative in the output result inc. formatters (WARN: leaks the file structure)"},
            })

    def get_cdn_url(self, media: Media) -> str:
        # TODO: is this viable with Storage.configs on path/filename?
        dest = os.path.join(self.save_to, media.key)
        if self.save_absolute:
            dest = os.path.abspath(dest)
        return dest

    def upload(self, media: Media, **kwargs) -> bool:
        # override parent so that we can use shutil.copy2 and keep metadata
        dest = os.path.join(self.save_to, media.key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        logger.debug(f'[{self.__class__.name}] storing file {media.filename} with key {media.key} to {dest}')
        res = shutil.copy2(media.filename, dest)
        logger.info(res)
        return True

    # must be implemented even if unused
    def uploadf(self, file: IO[bytes], key: str, **kwargs: dict) -> bool: pass
