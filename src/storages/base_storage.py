import os, uuid
from loguru import logger
from abc import ABC, abstractmethod
from pathlib import Path


class Storage(ABC):
    TMP_FOLDER = "tmp/"

    @abstractmethod
    def __init__(self, config): pass

    @abstractmethod
    def get_cdn_url(self, key): pass

    @abstractmethod
    def exists(self, key): pass

    @abstractmethod
    def uploadf(self, file, key, **kwargs): pass

    def clean_key(self, key):
        # Some storages does not work well with trailing forward slashes and some keys come with that
        if key.startswith('/'):
            logger.debug(f'Found and fixed a leading "/" for {key=}')
            return key[1:]
        return key


    def upload(self, filename: str, key: str, **kwargs):
        logger.debug(f'[{self.__class__.__name__}] uploading file {filename} with key {key}')
        with open(filename, 'rb') as f:
            self.uploadf(f, key, **kwargs)
