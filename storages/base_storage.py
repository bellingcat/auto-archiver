from abc import ABC, abstractmethod


class Storage(ABC):
    @abstractmethod
    def __init__(self, config): pass

    @abstractmethod
    def get_cdn_url(self, path): pass

    @abstractmethod
    def exists(self, path): pass

    @abstractmethod
    def uploadf(self, file, key, **kwargs): pass

    def upload(self, filename: str, key: str, **kwargs):
        with open(filename, 'rb') as f:
            self.uploadf(f, key, **kwargs)
