import datetime, os, yt_dlp, pysubs2
from loguru import logger

from . import Archiver
from ..core import Metadata, Media, ArchivingContext


class YoutubeDLArchiver(Archiver):
    name = "youtubedl_archiver"

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.subtitles = bool(self.subtitles)
        self.comments = bool(self.comments)

    @staticmethod
    def configs() -> dict:
        return {
            "facebook_cookie": {"default": None, "help": "optional facebook cookie to have more access to content, from browser, looks like 'cookie: datr= xxxx'"},
            "subtitles": {"default": True, "help": "download subtitles if available"},
            "comments": {"default": False, "help": "download all comments if available, may lead to large metadata"}
        }

    def download(self, item: Metadata) -> Metadata:
        #TODO: yt-dlp for transcripts?
        url = item.get_url()

        if item.netloc in ['facebook.com', 'www.facebook.com'] and self.facebook_cookie:
            logger.debug('Using Facebook cookie')
            yt_dlp.utils.std_headers['cookie'] = self.facebook_cookie

        ydl_options = {'outtmpl': os.path.join(ArchivingContext.get_tmp_dir(), f'%(id)s.%(ext)s'), 'quiet': False, 'noplaylist': True, 'writesubtitles': self.subtitles, 'writeautomaticsub': self.subtitles}
        ydl = yt_dlp.YoutubeDL(ydl_options) # allsubtitles and subtitleslangs not working as expected, so default lang is always "en"

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
        ydl = yt_dlp.YoutubeDL({**ydl_options, "getcomments": self.comments}) 
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
            new_media = Media(filename).set("duration", info.get("duration"))
            
            # read text from subtitles if enabled
            if self.subtitles:
                for lang, val in info.get('requested_subtitles', {}).items():
                    try:    
                        subs = pysubs2.load(val.get('filepath'), encoding="utf-8")
                        text = " ".join([line.text for line in subs])
                        new_media.set(f"subtitles_{lang}", text)
                    except Exception as e:
                        logger.error(f"Error loading subtitle file {val.get('filepath')}: {e}")
            result.add_media(new_media)

        # extract comments if enabled
        if self.comments:
            result.set("comments", [{
                "text": c["text"],
                "author": c["author"], 
                "timestamp": datetime.datetime.utcfromtimestamp(c.get("timestamp")).replace(tzinfo=datetime.timezone.utc)
            } for c in info.get("comments", [])])

        if (timestamp := info.get("timestamp")):
            timestamp = datetime.datetime.utcfromtimestamp(timestamp).replace(tzinfo=datetime.timezone.utc).isoformat()
            result.set_timestamp(timestamp)
        if (upload_date := info.get("upload_date")):
            upload_date = datetime.datetime.strptime(upload_date, '%Y%m%d').replace(tzinfo=datetime.timezone.utc)
            result.set("upload_date", upload_date)

        return result.success("yt-dlp")
