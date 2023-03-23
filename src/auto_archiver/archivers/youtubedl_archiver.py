import datetime, os, yt_dlp
from loguru import logger

from . import Archiver
from ..core import Metadata, Media, ArchivingContext


class YoutubeDLArchiver(Archiver):
    name = "youtubedl_archiver"

    def __init__(self, config: dict) -> None:
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {
            "facebook_cookie": {"default": None, "help": "optional facebook cookie to have more access to content, from browser, looks like 'cookie: datr= xxxx'"},
        }

    def download(self, item: Metadata) -> Metadata:
        #TODO: yt-dlp for transcripts?
        url = item.get_url()

        if item.netloc in ['facebook.com', 'www.facebook.com'] and self.facebook_cookie:
            logger.debug('Using Facebook cookie')
            yt_dlp.utils.std_headers['cookie'] = self.facebook_cookie

        ydl = yt_dlp.YoutubeDL({'outtmpl': os.path.join(ArchivingContext.get_tmp_dir(), f'%(id)s.%(ext)s'), 'quiet': False})

        try:
            # don'd download since it can be a live stream
            info = ydl.extract_info(url, download=False)
            if info.get('is_live', False):
                logger.warning("Live streaming media, not archiving now")
                return False
        except yt_dlp.utils.DownloadError as e:
            logger.debug(f'No video - Youtube normal control flow: {e}')
            return False
        except Exception as e:
            logger.debug(f'ytdlp exception which is normal for example a facebook page with images only will cause a IndexError: list index out of range. Exception here is: \n  {e}')
            return False

        # this time download
        info = ydl.extract_info(url, download=True)
        if "entries" in info:
            entries = info.get("entries", [])
            if not len(entries):
                logger.warning('YoutubeDLArchiver could not find any video')
                return False
        else: entries = [info]

        result = Metadata()
        result.set_title(info.get("title"))
        for entry in entries:
            filename = ydl.prepare_filename(entry)
            if not os.path.exists(filename):
                filename = filename.split('.')[0] + '.mkv'
            result.add_media(Media(filename).set("duration", info.get("duration")))

        if (timestamp := info.get("timestamp")):
            timestamp = datetime.datetime.utcfromtimestamp(timestamp).replace(tzinfo=datetime.timezone.utc).isoformat()
            result.set_timestamp(timestamp)
        if (upload_date := info.get("upload_date")):
            upload_date = datetime.datetime.strptime(upload_date, '%Y%m%d').replace(tzinfo=datetime.timezone.utc)
            result.set("upload_date", upload_date)

        return result.success("yt-dlp")
