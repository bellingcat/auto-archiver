import os, datetime, shutil, hashlib, time, requests, re, mimetypes, subprocess
from dataclasses import dataclass
from abc import ABC, abstractmethod
from urllib.parse import urlparse
from random import randrange

import ffmpeg
from loguru import logger
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from slugify import slugify

from configs import Config
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
    wacz: str = None
    hash: str = None

class Archiver(ABC):
    name = "default"
    retry_regex = r"retrying at (\d+)$"

    def __init__(self, storage: Storage, config: Config):
        self.storage = storage
        self.driver = config.webdriver
        self.hash_algorithm = config.hash_algorithm
        self.browsertrix = config.browsertrix_config

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__str__()

    @abstractmethod
    def download(self, url, check_if_exists=False): pass

    def get_netloc(self, url):
        return urlparse(url).netloc

    def generate_media_page_html(self, url, urls_info: dict, object, thumbnail=None):
        """
        Generates an index.html page where each @urls_info is displayed
        """
        page = f'''<html><head><title>{url}</title><meta charset="UTF-8"></head>
            <body>
            <h2>Archived media from {self.name}</h2>
            <h3><a href="{url}">{url}</a></h3><ul>'''

        for url_info in urls_info:
            mime_global = self._guess_file_type(url_info["key"])
            preview = ""
            if mime_global == "image":
                preview = f'<img src="{url_info["cdn_url"]}" style="max-height:200px;max-width:400px;"></img>'
            elif mime_global == "video":
                preview = f'<video src="{url_info["cdn_url"]}" controls style="max-height:400px;max-width:400px;"></video>'
            page += f'''<li><a href="{url_info['cdn_url']}">{preview}{url_info['key']}</a>: {url_info['hash']}</li>'''

        page += f"</ul><h2>{self.name} object data:</h2><code>{object}</code>"
        page += f"</body></html>"

        page_key = self.get_html_key(url)
        page_filename = os.path.join(Storage.TMP_FOLDER, page_key)

        with open(page_filename, "w") as f:
            f.write(page)

        page_hash = self.get_hash(page_filename)

        self.storage.upload(page_filename, page_key, extra_args={
            'ACL': 'public-read', 'ContentType': 'text/html'})

        page_cdn = self.storage.get_cdn_url(page_key)
        return (page_cdn, page_hash, thumbnail)

    def _guess_file_type(self, path: str):
        """
        Receives a URL or filename and returns global mimetype like 'image' or 'video'
        see https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
        """
        mime = mimetypes.guess_type(path)[0]
        if mime is not None:
            return mime.split("/")[0]
        return ""

    def download_from_url(self, url, to_filename):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
        }
        d = requests.get(url, headers=headers)
        with open(to_filename, 'wb') as f:
            f.write(d.content)

    def generate_media_page(self, urls, url, object):
        """
        For a list of media urls, fetch them, upload them
        and call self.generate_media_page_html with them
        """

        thumbnail = None
        uploaded_media = []
        for media_url in urls:
            key = self._get_key_from_url(media_url, ".jpg")

            filename = os.path.join(Storage.TMP_FOLDER, key)
            self.download_from_url(media_url, filename)
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

    def get_html_key(self, url):
        return self._get_key_from_url(url, ".html")

    def _get_key_from_url(self, url, with_extension: str = None, append_datetime: bool = False):
        """
        Receives a URL and returns a slugified version of the URL path
        if a string is passed in @with_extension the slug is appended with it if there is no "." in the slug
        if @append_date is true, the key adds a timestamp after the URL slug and before the extension
        """
        url_path = urlparse(url).path
        path, ext = os.path.splitext(url_path)
        slug = slugify(path)
        if append_datetime:
            slug += "-" + slugify(datetime.datetime.utcnow().isoformat())
        if len(ext):
            slug += ext
        if with_extension is not None:
            if "." not in slug:
                slug += with_extension
        return self.get_key(slug)

    def get_hash(self, filename):
        with open(filename, "rb") as f:
            bytes = f.read()  # read entire file as bytes
            logger.debug(f'Hash algorithm is {self.hash_algorithm}')

            if self.hash_algorithm == "SHA-256": hash = hashlib.sha256(bytes)
            elif self.hash_algorithm == "SHA3-512": hash = hashlib.sha3_512(bytes)
            else: raise Exception(f"Unknown Hash Algorithm of {self.hash_algorithm}")

        return hash.hexdigest()

    def get_screenshot(self, url):
        logger.debug(f"getting screenshot for {url=}")
        key = self._get_key_from_url(url, ".png", append_datetime=True)
        filename = os.path.join(Storage.TMP_FOLDER, key)

        # Accept cookies popup dismiss for ytdlp video
        if 'facebook.com' in url:
            try:
                logger.debug(f'Trying fb click accept cookie popup for {url}')
                self.driver.get("http://www.facebook.com")
                foo = self.driver.find_element(By.XPATH, "//button[@data-cookiebanner='accept_only_essential_button']")
                foo.click()
                logger.debug(f'fb click worked')
                # linux server needs a sleep otherwise facebook cookie won't have worked and we'll get a popup on next page
                time.sleep(2)
            except:
                logger.warning(f'Failed on fb accept cookies for url {url}')

        try:
            self.driver.get(url)
            time.sleep(6)
        except TimeoutException:
            logger.info("TimeoutException loading page for screenshot")

        self.driver.save_screenshot(filename)
        self.storage.upload(filename, key, extra_args={
                            'ACL': 'public-read', 'ContentType': 'image/png'})

        return self.storage.get_cdn_url(key)

    def get_wacz(self, url):
        logger.debug(f"getting wacz for {url}")
        key = self._get_key_from_url(url, ".wacz", append_datetime=True)
        collection = key.replace(".wacz", "").replace("-", "")

        browsertrix_home = os.path.join(os.getcwd(), "browsertrix")
        cmd = [
            "docker", "run",
            "-v", f"{browsertrix_home}:/crawls/",
            "-it",
            "webrecorder/browsertrix-crawler", "crawl",
            "--url", url,
            "--scopeType", "page",
            "--generateWACZ",
            "--text",
            "--collection", collection,
            "--behaviors", "autoscroll,autoplay,autofetch,siteSpecific",
            "--behaviorTimeout", "90"
        ]

        if not os.path.isdir(browsertrix_home):
            os.mkdir(browsertrix_home)

        if self.browsertrix.profile:
            shutil.copyfile(self.browsertrix.profile, os.path.join(browsertrix_home, "profile.tar.gz"))
            cmd.extend(["--profile", "/crawls/profile.tar.gz"])

        try:
            logger.info(f"Running browsertrix-crawler: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
        except Exception as e:
            logger.error(f"WACZ generation failed: {e}")
            return

        filename = os.path.join(browsertrix_home, "collections", collection, f"{collection}.wacz")

        self.storage.upload(filename, key, extra_args={
                            'ACL': 'public-read', 'ContentType': 'application/zip'})

        # clean up the local browsertrix files
        try:
            shutil.rmtree(browsertrix_home)
        except PermissionError:
            logger.warn(f"Unable to clean up browsertrix-crawler files in {browsertrix_home}")

        return self.storage.get_cdn_url(key)

    def get_thumbnails(self, filename, key, duration=None):
        thumbnails_folder = os.path.splitext(filename)[0] + os.path.sep
        key_folder = key.split('.')[0] + os.path.sep

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
                key = os.path.join(key_folder, fname)

                self.storage.upload(thumbnail_filename, key)
                cdn_url = self.storage.get_cdn_url(key)
                cdn_urls.append(cdn_url)

        if len(cdn_urls) == 0:
            return ('', '')

        key_thumb = cdn_urls[int(len(cdn_urls) * 0.1)]

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

    def signal_retry_in(self, min_seconds=1800, max_seconds=7200, **kwargs):
        """
        sets state to retry in random between (min_seconds, max_seconds)
        """
        now = datetime.datetime.now().timestamp()
        retry_at = int(now + randrange(min_seconds, max_seconds))
        logger.debug(f"signaling {retry_at=}")
        return ArchiveResult(status=f'retrying at {retry_at}', **kwargs)

    def is_retry(status):
        return re.search(Archiver.retry_regex, status) is not None

    def should_retry_from_status(status):
        """
        checks status against message in signal_retry_in
        returns true if enough time has elapsed, false otherwise
        """
        match = re.search(Archiver.retry_regex, status)
        if match:
            retry_at = int(match.group(1))
            now = datetime.datetime.now().timestamp()
            should_retry = now >= retry_at
            logger.debug(f"{should_retry=} since {now=} and {retry_at=}")
            return should_retry
        return False

    def remove_retry(status):
        """
        transforms the status from retry into something else
        """
        new_status = re.sub(Archiver.retry_regex, "failed: too many retries", status, 0)
        logger.debug(f"removing retry message at {status=}, got {new_status=}")
        return new_status
