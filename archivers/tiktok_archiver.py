import os, traceback
from botocore.errorfactory import ClientError
import tiktok_downloader
from loguru import logger
from .base_archiver import Archiver, ArchiveResult

# TODO: get_cdn_url, do_s3_upload, get_thumbnails


class TiktokArchiver(Archiver):
    name = "tiktok"
    
    def download(self, url, check_if_exists=False):
        if 'tiktok.com' not in url:
            return False

        status = 'success'

        try:
            info = tiktok_downloader.info_post(url)
            key = 'tiktok_' + str(info.id) + '.mp4'
            filename = 'tmp/' + key

            if check_if_exists:
                try:
                    self.s3.head_object(Bucket=os.getenv('DO_BUCKET'), Key=key)

                    # file exists
                    cdn_url = self.get_cdn_url(key)

                    status = 'already archived'

                except ClientError:
                    pass

            if status != 'already archived':
                media = tiktok_downloader.snaptik(url).get_media()
                if len(media) > 0:
                    media[0].download(filename)
                    with open(filename, 'rb') as f:
                        self.do_s3_upload(f, key)

                    cdn_url = self.get_cdn_url(key)
                else:
                    status = 'could not download media'

            try:
                key_thumb, thumb_index = self.get_thumbnails(
                    filename, duration=info.duration)
            except:
                key_thumb = ''
                thumb_index = 'error creating thumbnails'

            try: os.remove(filename)
            except FileNotFoundError:
                logger.info(f'tmp file not found thus not deleted {filename}')

            return ArchiveResult(status=status, cdn_url=cdn_url, thumbnail=key_thumb,
                                 thumbnail_index=thumb_index, duration=info.duration, title=info.caption, timestamp=info.create.isoformat())

        except tiktok_downloader.Except.InvalidUrl:
            status = 'Invalid URL'
            return ArchiveResult(status=status)

        except:
            error = traceback.format_exc()
            status = 'Other Tiktok error: ' + str(error)
            return ArchiveResult(status=status)
