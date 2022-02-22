import os
import ffmpeg
import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod

from storages import Storage


@dataclass
class ArchiveResult:
    status: str
    cdn_url: str = None
    thumbnail: str = None
    thumbnail_index: str = None
    duration: float = None
    title: str = None
    timestamp: datetime.datetime = None


class Archiver(ABC):
    name = "default"

    def __init__(self, storage: Storage):
        self.storage = storage

    def __str__(self):
        return self.__class__.__name__

    @abstractmethod
    def download(self, url, check_if_exists=False): pass

    def get_key(self, filename):
        """
        returns a key in the format "[archiverName]_[filename]" includes extension
        """
        tail = os.path.split(filename)[1]  # returns filename.ext from full path
        _id, extension = os.path.splitext(tail)  # returns [filename, .ext]
        if 'unknown_video' in _id:
            _id = _id.replace('unknown_video', 'jpg')
        return f'{self.name}_{_id}{extension}'

    def get_thumbnails(self, filename, duration=None):
        if not os.path.exists(filename.split('.')[0]):
            os.mkdir(filename.split('.')[0])

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
        stream.output(filename.split('.')[0] + '/out%d.jpg').run()

        thumbnails = os.listdir(filename.split('.')[0] + '/')
        cdn_urls = []

        for fname in thumbnails:
            if fname[-3:] == 'jpg':
                thumbnail_filename = filename.split('.')[0] + '/' + fname
                key = filename.split('/')[1].split('.')[0] + '/' + fname

                cdn_url = self.storage.get_cdn_url(key)

                self.storage.upload(thumbnail_filename, key)

                cdn_urls.append(cdn_url)
                os.remove(thumbnail_filename)

        if len(cdn_urls) == 0:
            return ('None', 'None')

        key_thumb = cdn_urls[int(len(cdn_urls) * 0.1)]

        index_page = f'''<html><head><title>{filename}</title></head>
            <body>'''

        for t in cdn_urls:
            index_page += f'<img src="{t}" />'

        index_page += f"</body></html>"
        index_fname = filename.split('.')[0] + '/index.html'

        with open(index_fname, 'w') as f:
            f.write(index_page)

        thumb_index = filename.split('/')[1].split('.')[0] + '/index.html'

        self.storage.upload(index_fname, thumb_index, extra_args={'ACL': 'public-read', 'ContentType': 'text/html'})

        thumb_index_cdn_url = self.storage.get_cdn_url(thumb_index)

        return (key_thumb, thumb_index_cdn_url)
