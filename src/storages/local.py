
import shutil
from typing import IO, Any
import boto3, uuid, os, mimetypes
from botocore.errorfactory import ClientError
from metadata import Metadata
from media import Media
from storages import StorageV2
from loguru import logger
from slugify import slugify


class LocalStorageV2(StorageV2):
    name = "local_storage"

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        os.makedirs(self.save_to, exist_ok=True)

    @staticmethod
    def configs() -> dict:
        return {
            "save_to": {"default": "./archived", "help": "folder where to save archived content"},
            "flatten": {"default": True, "help": "if true saves all files to the root of 'save_to' directory, if false preserves subdir structure"},
            "save_absolute": {"default": False, "help": "whether the path to the stored file is absolute or relative (leaks the file structure)"},
        }

    def get_cdn_url(self, media: Media) -> str:
        dest = os.path.join(self.save_to, media.key)
        if self.save_absolute:
            dest = os.path.abspath(dest)
        return dest

    def upload(self, media: Media, **kwargs) -> bool:
        # override parent so that we can use shutil.copy2 and keep metadata
        if self.flatten:
            dest = os.path.join(self.save_to, slugify(media.key))
        else:
            dest = os.path.join(self.save_to, media.key)

        os.makedirs(dest, exist_ok=True)
        logger.debug(f'[{self.__class__.name}] storing file {media.filename} with key {media.key} to {dest}')
        shutil.copy2(media.filename, dest)
        return True

    def uploadf(self, file: IO[bytes], key: str, **kwargs: dict) -> bool: pass
