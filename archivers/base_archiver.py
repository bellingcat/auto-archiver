import os
import ffmpeg
import datetime
import shutil
from dataclasses import dataclass
from abc import ABC, abstractmethod
from urllib.parse import urlparse
import hashlib
import time
import requests

from storages import Storage
from utils import mkdir_if_not_exists

from selenium.webdriver.common.by import By
from loguru import logger
from selenium.common.exceptions import TimeoutException

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

    def get_html_key(self, url):
        return self.get_key(urlparse(url).path.replace("/", "_") + ".html")

    # DM added UTF
    # https://github.com/bellingcat/auto-archiver/pull/21/commits/576f1a8f687199cf38864f7271b9a63e65de8692
    def generate_media_page_html(self, url, urls_info: dict, object, thumbnail=None):
        page = f'''<html><head><title>{url}</title><meta charset="UTF-8"></head>
            <body>
            <h2>Archived media from {self.name}</h2>
            <h3><a href="{url}">{url}</a></h3><ul>'''

        for url_info in urls_info:
            page += f'''<li><a href="{url_info['cdn_url']}">{url_info['key']}</a>: {url_info['hash']}</li>'''

        page += f"</ul><h2>{self.name} object data:</h2><code>{object}</code>"
        page += f"</body></html>"

        page_key = self.get_key(urlparse(url).path.replace("/", "_") + ".html")
        page_filename = 'tmp/' + page_key
        page_cdn = self.storage.get_cdn_url(page_key)

        with open(page_filename, "w") as f:
            f.write(page)

        page_hash = self.get_hash(page_filename)

        self.storage.upload(page_filename, page_key, extra_args={
            'ACL': 'public-read', 'ContentType': 'text/html'})
        return (page_cdn, page_hash, thumbnail)

    def generate_media_page(self, urls, url, object):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
        }

        thumbnail = None
        uploaded_media = []
        for media_url in urls:
            path = urlparse(media_url).path
            key = self.get_key(path.replace("/", "_"))
            if '.' not in path:
                key += '.jpg'

            filename = 'tmp/' + key

            d = requests.get(media_url, headers=headers)
            with open(filename, 'wb') as f:
                f.write(d.content)

            self.storage.upload(filename, key)
            hash = self.get_hash(filename)
            cdn_url = self.storage.get_cdn_url(key)

            if thumbnail is None:
                thumbnail = cdn_url
            uploaded_media.append({'cdn_url': cdn_url, 'key': key, 'hash': hash})

        return self.generate_media_page_html(url, uploaded_media, object, thumbnail=thumbnail)
    def get_key(self, filename):
        """
        returns a key in the format "[archiverName]_[filename]" includes extension
        """
        tail = os.path.split(filename)[1]  # returns filename.ext from full path
        _id, extension = os.path.splitext(tail)  # returns [filename, .ext]
        if 'unknown_video' in _id:
            _id = _id.replace('unknown_video', 'jpg')

        # long filenames can cause problems, so trim them if necessary
        if len(_id) > 128:
            _id = _id[-128:]

        return f'{self.name}_{_id}{extension}'

    def get_hash(self, filename):
        f = open(filename, "rb")
        bytes = f.read()  # read entire file as bytes
        # DM changed hash for CIR
        # hash = hashlib.sha256(bytes)
        hash = hashlib.sha3_512(bytes)
        f.close()
        return hash.hexdigest()

    def get_screenshot(self, url):
        key = self.get_key(urlparse(url).path.replace(
            "/", "_") + datetime.datetime.utcnow().isoformat().replace(" ", "_") + ".png")
        filename = 'tmp/' + key

        # DM - Accept cookies popup dismiss for ytdlp video
        if 'facebook.com' in url:
            try:
                logger.debug(f'Trying fb click accept cookie popup for {url}')
                self.driver.get("http://www.facebook.com") 
                foo = self.driver.find_element(By.XPATH,"//button[@data-cookiebanner='accept_only_essential_button']")
                foo.click()
                logger.debug(f'fb click worked')
                # linux server needs a sleep otherwise facebook cookie wont have worked and we'll get a popup on next page
                time.sleep(2)
                # DM some FB videos needs to be logged in
            except:
                logger.warning(f'Failed on fb accept cookies for url {url}')
        
        try: 
            self.driver.get(url)
            time.sleep(6)
        except TimeoutException:
            logger.info("TimeoutException loading page for screenshot")

        self.driver.save_screenshot(filename)

        # want to reset so that next call to selenium doesn't have cookies?
        # functions needs to be idempotent

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

        # DM added UTF
        # https://github.com/bellingcat/auto-archiver/pull/21/commits/576f1a8f687199cf38864f7271b9a63e65de8692
        index_page = f'''<html><head><title>{filename}</title><meta charset="UTF-8"></head>
            <body>'''

        for t in cdn_urls:
            index_page += f'<img src="{t}" />'

        index_page += f"</body></html>"
        index_fname = thumbnails_folder + 'index.html'

        with open(index_fname, 'w') as f:
            f.write(index_page)

        thumb_index = key_folder + 'index.html'

        self.storage.upload(index_fname, thumb_index, extra_args={
                            'ACL': 'public-read', 'ContentType': 'text/html'})
        shutil.rmtree(thumbnails_folder)

        thumb_index_cdn_url = self.storage.get_cdn_url(thumb_index)

        return (key_thumb, thumb_index_cdn_url)
