
import os
import datetime
import youtube_dl
from loguru import logger
from botocore.errorfactory import ClientError
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
                    logger.warning(
                        'YoutubeDLArchiver cannot archive channels or pages with multiple videos')
                    return False

                filename = ydl.prepare_filename(info['entries'][0])
            else:
                filename = ydl.prepare_filename(info)

            key = self.get_key(filename)

            try:
                self.s3.head_object(Bucket=os.getenv('DO_BUCKET'), Key=key)

                # file exists
                cdn_url = self.get_cdn_url(key)

                status = 'already archived'

            except ClientError:
                pass

        # sometimes this results in a different filename, so do this again
        info = ydl.extract_info(url, download=True)

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
            key = self. get_key(filename)
            cdn_url = self.get_cdn_url(key)

            with open(filename, 'rb') as f:
                self.do_s3_upload(f, key)

        # get duration
        duration = info['duration'] if 'duration' in info else None

        # get thumbnails
        key_thumb, thumb_index = self.get_thumbnails(filename, duration=duration)
        os.remove(filename)

        return ArchiveResult(status=status, cdn_url=cdn_url, thumbnail=key_thumb, thumbnail_index=thumb_index, duration=duration,
                             title=info['title'] if 'title' in info else None,
                             timestamp=info['timestamp'] if 'timestamp' in info else datetime.datetime.strptime(info['upload_date'], '%Y%m%d').timestamp() if 'upload_date' in info else None)
