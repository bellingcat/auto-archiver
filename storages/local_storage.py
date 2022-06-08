import os

from dataclasses import dataclass

from .base_storage import Storage
from utils import mkdir_if_not_exists


@dataclass
class LocalConfig:
    folder: str = ""
    save_to: str = "./"

class LocalStorage(Storage):
    def __init__(self, config:LocalConfig):
        self.folder = config.folder
        self.save_to = config.save_to
        mkdir_if_not_exists(self.save_to)

    def get_cdn_url(self, key):
        full_path = os.path.join(self.save_to, self.folder, key)
        mkdir_if_not_exists(os.path.join(*full_path.split(os.path.sep)[0:-1]))
        return os.path.abspath(full_path)

    def exists(self, key):
        return os.path.isfile(self.get_cdn_url(key))

    def uploadf(self, file, key, **kwargs):
        path = self.get_cdn_url(key)
        with open(path, "wb") as outf:
            outf.write(file.read())
