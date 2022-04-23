
import os
import datetime
import yt_dlp
from loguru import logger

from .base_archiver import Archiver, ArchiveResult
from storages import Storage

class YoutubeDLArchiver(Archiver):
    name = "youtube_dl"
    ydl_opts = {'outtmpl': 'tmp/%(id)s.%(ext)s', 'quiet': False}

    # DM added so can pass in facebook cookie from .env
    def __init__(self, storage: Storage, driver, fb_cookie):
        super().__init__(storage, driver)
        self.fb_cookie = fb_cookie

    def download(self, url, check_if_exists=False):
        netloc = self.get_netloc(url)
        # DM to set env variable: export FB_COOKIE="paste"
        # this gets blanked at the end of each session ie when vs code closes
        # if netloc in ['facebook.com', 'www.facebook.com'] and os.getenv('FB_COOKIE'):
        if netloc in ['facebook.com', 'www.facebook.com']:
            logger.info('Using Facebook cookie')
            # yt_dlp.utils.std_headers['cookie'] = os.getenv('FB_COOKIE')
            yt_dlp.utils.std_headers['cookie'] = self.fb_cookie

        ydl = yt_dlp.YoutubeDL(YoutubeDLArchiver.ydl_opts)
        cdn_url = None
        status = 'success'

        try:
            info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError:
            # no video here
            return False
        # DM Exception is actually normal control flow!
        # todo
        except Exception as e:
            logger.debug(f'ytdlp exception which is normal for example a facebook page with images only will cause a IndexError: list index out of range. Exception here is: \n  {e}')
            return False

        if info.get('is_live', False):
            logger.warning("Live streaming media, not archiving now")
            return ArchiveResult(status="Streaming media")

        #DM
        if 'twitter.com' in netloc:
            if 'https://twitter.com/' in info['webpage_url']:
                logger.info('Found https://twitter.com/ in the download url from Twitter')
            else:
                logger.warning('Found a linked video probably in a link in a tweet - not getting that video as there may be images in the tweet')
                return False

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

        hash = self.get_hash(filename)
        screenshot = self.get_screenshot(url)

        # get duration
        duration = info.get('duration')

        # get thumbnails
        try:
            key_thumb, thumb_index = self.get_thumbnails(filename, key, duration=duration)
        except:
            key_thumb = ''
            thumb_index = 'Could not generate thumbnails'

        os.remove(filename)

        timestamp = datetime.datetime.utcfromtimestamp(info['timestamp']).replace(tzinfo=datetime.timezone.utc).isoformat() \
            if 'timestamp' in info else \
                datetime.datetime.strptime(info['upload_date'], '%Y%m%d').replace(tzinfo=datetime.timezone.utc) \
            if 'upload_date' in info and info['upload_date'] is not None else \
                None

        return ArchiveResult(status=status, cdn_url=cdn_url, thumbnail=key_thumb, thumbnail_index=thumb_index, duration=duration,
                             title=info['title'] if 'title' in info else None, timestamp=timestamp, hash=hash, screenshot=screenshot)
