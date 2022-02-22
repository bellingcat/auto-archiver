
import os
import datetime
import youtube_dl
from loguru import logger

from .base_archiver import Archiver, ArchiveResult


class YoutubeDLArchiver(Archiver):
    name = "yotube_dl"

    def download(self, url, check_if_exists=False):
        ydl_opts = {'outtmpl': 'tmp/%(id)s.%(ext)s', 'quiet': False}
        if (url[0:21] == 'https://facebook.com/' or url[0:25] == 'https://wwww.facebook.com/') and os.getenv('FB_COOKIE'):
            logger.info('Using Facebook cookie')
            youtube_dl.utils.std_headers['cookie'] = os.getenv('FB_COOKIE')

        ydl = youtube_dl.YoutubeDL(ydl_opts)
        cdn_url = None
        status = 'success'

        try:
            info = ydl.extract_info(url, download=False)
        except youtube_dl.utils.DownloadError:
            # no video here
            return False

        if 'is_live' in info and info['is_live']:
            logger.warning("Live streaming media, not archiving now")
            return ArchiveResult(status="Streaming media")

        if check_if_exists:
            if 'entries' in info:
                if len(info['entries']) > 1:
                    logger.warning('YoutubeDLArchiver succeeded but cannot archive channels or pages with multiple videos')
                    return False
                elif len(info['entries']) == 0:
                    logger.warning(
                        'YoutubeDLArchiver succeeded but did not find video')
                    return False

                filename = ydl.prepare_filename(info['entries'][0])
            else:
                filename = ydl.prepare_filename(info)

            key = self.get_key(filename)

            if self.storage.exists(key):
                status = 'already archived'
                cdn_url = self.storage.get_cdn_url(key)

        # sometimes this results in a different filename, so do this again
        info = ydl.extract_info(url, download=True)

        # TODO: add support for multiple videos
        if 'entries' in info:
            if len(info['entries']) > 1:
                logger.warning(
                    'YoutubeDLArchiver cannot archive channels or pages with multiple videos')
                return False
            else:
                info = info['entries'][0]

        filename = ydl.prepare_filename(info)

        if not os.path.exists(filename):
            filename = filename.split('.')[0] + '.mkv'

        if status != 'already archived':
            key = self.get_key(filename)
            cdn_url = self.storage.get_cdn_url(key)

            self.storage.upload(filename, key)

        # get duration
        duration = info['duration'] if 'duration' in info else None

        # get thumbnails
        try:
            key_thumb, thumb_index = self.get_thumbnails(filename, duration=duration)
        except:
            key_thumb = ''
            thumb_index = 'Could not generate thumbnails'

        os.remove(filename)

        timestamp = info['timestamp'] if 'timestamp' in info else datetime.datetime.strptime(info['upload_date'], '%Y%m%d').timestamp() if 'upload_date' in info and info['upload_date'] is not None else None

        return ArchiveResult(status=status, cdn_url=cdn_url, thumbnail=key_thumb, thumbnail_index=thumb_index, duration=duration,
                             title=info['title'] if 'title' in info else None, timestamp=timestamp)
