import os
from .base_storage import Storage


class LocalStorage(Storage):
    def __init__(self, folder):
        self.folder = folder
        if len(self.folder) and self.folder[-1] != '/':
            self.folder += '/'

    def get_cdn_url(self, key):
        return self.folder + key

    def exists(self, key):
        return os.path.isfile(self.get_cdn_url(key))

    def uploadf(self, file, key, **kwargs):
        path = self.get_cdn_url(key)
        with open(path, "wb") as outf:
            outf.write(file.read())
