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

    def upload(self, filename: str, key: str, **kwargs):
        logger.debug(f'[{self.__class__.__name__}] uploading file {filename} with key {key}')
        with open(filename, 'rb') as f:
            self.uploadf(f, key, **kwargs)

    def update_properties(self, **kwargs):
        """
        method used to update general properties that some children may use 
        and others not, but that all can call
        """
        for k, v in kwargs.items():
            if k in self.get_allowed_properties():
                setattr(self, k, v)
            else:
                logger.warning(f'[{self.__class__.__name__}] does not accept dynamic property "{k}"')

    def get_allowed_properties(self):
        """
        child classes should specify which properties they allow to be set
        """
        return set(["subfolder"])

    def clean_path(self, folder, default="", add_forward_slash=True):
        if folder is None or type(folder) != str or len(folder.strip()) == 0:
            return default
        return str(Path(folder)) + ("/" if add_forward_slash else "")
