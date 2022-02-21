import os
import ffmpeg
from dataclasses import dataclass
import datetime
from loguru import logger

# TODO There should be a better way of generating keys, that adds the following info:
#           - name of sheet that it is being archived from
#             (this means we might archive the same media twice on different sheets, but that's OK I think)
#           - name of archiver/platform that the video comes from
#       This should make it easier to maintain and clean the archive later

# TODO "check_if_exists" has lots of repeated code across the archivers. Can this be
#      cleaned up? Difficult is we don't know the filename until the archivers start working.


@dataclass
class ArchiveResult:
    status: str
    cdn_url: str = None
    thumbnail: str = None
    thumbnail_index: str = None
    duration: float = None
    title: str = None
    timestamp: datetime.datetime = None


class Archiver:
    name = "default"

    def __init__(self, s3_client):
        self.s3 = s3_client

    def __str__(self):
        return self.__class__.__name__

    def download(self, url, check_if_exists=False):
        logger.error("method 'download' not implemented")

    def get_cdn_url(self, key):
        return 'https://{}.{}.cdn.digitaloceanspaces.com/{}'.format(
            os.getenv('DO_BUCKET'), os.getenv('DO_SPACES_REGION'), key)

    def do_s3_upload(self, f, key):
        self.s3.upload_fileobj(f, Bucket=os.getenv(
            'DO_BUCKET'), Key=key, ExtraArgs={'ACL': 'public-read'})

    def get_key(self, filename):
        print(f"key base implementation: {self.name}")
        # TODO: refactor to be more manageable
        key = filename.split('/')[1]
        if 'unknown_video' in key:
            key = key.replace('unknown_video', 'jpg')
        return key

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

                cdn_url = self.get_cdn_url(key)

                with open(thumbnail_filename, 'rb') as f:
                    self.do_s3_upload(f, key)

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

        self.s3.upload_fileobj(open(index_fname, 'rb'), Bucket=os.getenv(
            'DO_BUCKET'), Key=thumb_index, ExtraArgs={'ACL': 'public-read', 'ContentType': 'text/html'})

        thumb_index_cdn_url = self.get_cdn_url(thumb_index)

        return (key_thumb, thumb_index_cdn_url)
