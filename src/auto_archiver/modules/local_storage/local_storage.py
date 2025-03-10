
import shutil
from typing import IO
import os
from loguru import logger

from auto_archiver.core import Media
from auto_archiver.core import Storage


class LocalStorage(Storage):

    MAX_FILE_LENGTH = 255

    def get_cdn_url(self, media: Media) -> str:
        # TODO: is this viable with Storage.configs on path/filename?
        dest = os.path.join(self.save_to, media.key)
        if self.save_absolute:
            dest = os.path.abspath(dest)
        return dest

    def upload(self, media: Media, **kwargs) -> bool:
        # override parent so that we can use shutil.copy2 and keep metadata
        dest = os.path.join(self.save_to, media.key)

        if len(dest) > self.max_file_length():
            old_dest_length = len(dest)
            filename, ext = os.path.splitext(media.key)
            dir, filename = os.path.split(filename)
            # see whether we should truncate filename or dir
            if len(dir) > len(filename):
                dir = dir[:self.MAX_FILE_LENGTH - len(self.save_to) - len(ext) - len(filename) - 1]
            else:
                filename = filename[:self.MAX_FILE_LENGTH - len(self.save_to) - len(ext) - len(filename) - 1]

            # override media.key
            media.key = os.path.join(dir, f"{filename}{ext}")
            dest = os.path.join(self.save_to, dir, f"{filename}{ext}")
            logger.warning(f'Filename too long ({old_dest_length} characters), truncating to {len(dest)} characters')

        os.makedirs(os.path.dirname(dest), exist_ok=True)
        logger.debug(f'[{self.__class__.__name__}] storing file {media.filename} with key {media.key} to {dest}')

        res = shutil.copy2(media.filename, dest)
        logger.info(res)
        return True

    # must be implemented even if unused
    def uploadf(self, file: IO[bytes], key: str, **kwargs: dict) -> bool: pass

    def max_file_length(self):
        return self.MAX_FILE_LENGTH