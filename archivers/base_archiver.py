import os
import ffmpeg
import datetime
import shutil
from dataclasses import dataclass
from abc import ABC, abstractmethod
from urllib.parse import urlparse
import hashlib
from selenium.common.exceptions import TimeoutException
from loguru import logger
import time

from storages import Storage
from utils import mkdir_if_not_exists


@dataclass
class ArchiveResult:
    status: str
    cdn_url: str = None
    thumbnail: str = None
    thumbnail_index: str = None
    duration: float = None
    title: str = None
    timestamp: datetime.datetime = None
    screenshot: str = None
    hash: str = None


class Archiver(ABC):
    name = "default"

    def __init__(self, storage: Storage, driver):
        self.storage = storage
        self.driver = driver

    def __str__(self):
        return self.__class__.__name__

    @abstractmethod
    def download(self, url, check_if_exists=False): pass

    def get_netloc(self, url):
        return urlparse(url).netloc

    def get_key(self, filename):
        """
        returns a key in the format "[archiverName]_[filename]" includes extension
        """
        tail = os.path.split(filename)[1]  # returns filename.ext from full path
        _id, extension = os.path.splitext(tail)  # returns [filename, .ext]
        if 'unknown_video' in _id:
            _id = _id.replace('unknown_video', 'jpg')
        return f'{self.name}_{_id}{extension}'

    def get_hash(self, filename):
        f = open(filename, "rb")
        bytes = f.read()  # read entire file as bytes
        hash = hashlib.sha256(bytes)
        f.close()
        return hash.hexdigest()

    def get_screenshot(self, url):
        key = self.get_key(urlparse(url).path.replace(
            "/", "_") + datetime.datetime.utcnow().isoformat().replace(" ", "_") + ".png")
        filename = 'tmp/' + key

        self.driver.get(url)
        time.sleep(6)

        self.driver.save_screenshot(filename)
        self.storage.upload(filename, key, extra_args={
                            'ACL': 'public-read', 'ContentType': 'image/png'})
        return self.storage.get_cdn_url(key)

    def get_thumbnails(self, filename, key, duration=None):
        thumbnails_folder = filename.split('.')[0] + '/'
        key_folder = key.split('.')[0] + '/'

        mkdir_if_not_exists(thumbnails_folder)

        fps = 0.5
        if duration is not None:
            duration = float(duration)

            if duration < 60:
                fps = 10.0 / duration
            elif duration < 120:
                fps = 20.0 / duration
            else:
                fps = 40.0 / duration

        stream = ffmpeg.input(filename)
        stream = ffmpeg.filter(stream, 'fps', fps=fps).filter('scale', 512, -1)
        stream.output(thumbnails_folder + 'out%d.jpg').run()

        thumbnails = os.listdir(thumbnails_folder)
        cdn_urls = []
        for fname in thumbnails:
            if fname[-3:] == 'jpg':
                thumbnail_filename = thumbnails_folder + fname
                key = key_folder + fname

                cdn_url = self.storage.get_cdn_url(key)

                self.storage.upload(thumbnail_filename, key)

                cdn_urls.append(cdn_url)

        if len(cdn_urls) == 0:
            return ('None', 'None')

        key_thumb = cdn_urls[int(len(cdn_urls) * 0.1)]

        index_page = f'''<html><head><title>{filename}</title></head>
            <body>'''

        for t in cdn_urls:
            index_page += f'<img src="{t}" />'

        index_page += f"</body></html>"
        index_fname = thumbnails_folder + 'index.html'

        with open(index_fname, 'w') as f:
            f.write(index_page)

        thumb_index = key_folder + 'index.html'

        self.storage.upload(index_fname, thumb_index, extra_args={'ACL': 'public-read', 'ContentType': 'text/html'})
        shutil.rmtree(thumbnails_folder)

        thumb_index_cdn_url = self.storage.get_cdn_url(thumb_index)

        return (key_thumb, thumb_index_cdn_url)
