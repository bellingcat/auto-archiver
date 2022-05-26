import os, traceback
import tiktok_downloader
from loguru import logger

from .base_archiver import Archiver, ArchiveResult


class TiktokArchiver(Archiver):
    name = "tiktok"

    def download(self, url, check_if_exists=False):
        if 'tiktok.com' not in url:
            return False

        status = 'success'

        try:
            info = tiktok_downloader.info_post(url)
            key = self.get_key(f'{info.id}.mp4')
            cdn_url = self.storage.get_cdn_url(key)
            filename = 'tmp/' + key

            if check_if_exists and self.storage.exists(key):
                status = 'already archived'

            media = tiktok_downloader.snaptik(url).get_media()

            if len(media) <= 0:
                if status == 'already archived':
                    return ArchiveResult(status='Could not download media, but already archived', cdn_url=cdn_url)
                else:
                    return ArchiveResult(status='Could not download media')

            media[0].download(filename)

            if status != 'already archived':
                self.storage.upload(filename, key)

            try:
                key_thumb, thumb_index = self.get_thumbnails(filename, key, duration=info.duration)
            except Exception as e:
                logger.error(e)
                key_thumb = ''
                thumb_index = 'error creating thumbnails'

            hash = self.get_hash(filename)
            screenshot = self.get_screenshot(url)

            try: os.remove(filename)
            except FileNotFoundError:
                logger.info(f'tmp file not found thus not deleted {filename}')

            return ArchiveResult(status=status, cdn_url=cdn_url, thumbnail=key_thumb,
                                 thumbnail_index=thumb_index, duration=info.duration, title=info.caption, timestamp=info.create.isoformat(),
                                 hash=hash, screenshot=screenshot)

        except tiktok_downloader.Except.InvalidUrl as e:
            status = 'Invalid URL'
            logger.warning(f'Invalid URL on {url}  {e}\n{traceback.format_exc()}')
            return ArchiveResult(status=status)

        except:
            error = traceback.format_exc()
            status = 'Other Tiktok error: ' + str(error)
            logger.warning(f'Other Tiktok error' + str(error))
            return ArchiveResult(status=status)
