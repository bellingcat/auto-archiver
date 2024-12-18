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
        self.livestreams = bool(self.livestreams)
        self.live_from_start = bool(self.live_from_start)
        self.end_means_success = bool(self.end_means_success)
        self.allow_playlist = bool(self.allow_playlist)
        self.max_downloads = self.max_downloads

    @staticmethod
    def configs() -> dict:
        return {
            "facebook_cookie": {"default": None, "help": "optional facebook cookie to have more access to content, from browser, looks like 'cookie: datr= xxxx'"},
            "subtitles": {"default": True, "help": "download subtitles if available"},
            "comments": {"default": False, "help": "download all comments if available, may lead to large metadata"},
            "livestreams": {"default": False, "help": "if set, will download live streams, otherwise will skip them; see --max-filesize for more control"},
            "live_from_start": {"default": False, "help": "if set, will download live streams from their earliest available moment, otherwise starts now."},
            "proxy": {"default": "", "help": "http/socks (https seems to not work atm) proxy to use for the webdriver, eg https://proxy-user:password@proxy-ip:port"},
            "end_means_success": {"default": True, "help": "if True, any archived content will mean a 'success', if False this archiver will not return a 'success' stage; this is useful for cases when the yt-dlp will archive a video but ignore other types of content like images or text only pages that the subsequent archivers can retrieve."},
            'allow_playlist': {"default": False, "help": "If True will also download playlists, set to False if the expectation is to download a single video."},
            "max_downloads": {"default": "inf", "help": "Use to limit the number of videos to download when a channel or long page is being extracted. 'inf' means no limit."},
            "cookies_from_browser": {"default": None, "help": "optional browser for ytdl to extract cookies from, can be one of: brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale"},
            "cookie_file": {"default": None, "help": "optional cookie file to use for Youtube, see instructions here on how to export from your browser: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"},
        }

    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()

        if item.netloc in ['facebook.com', 'www.facebook.com'] and self.facebook_cookie:
            logger.debug('Using Facebook cookie')
            yt_dlp.utils.std_headers['cookie'] = self.facebook_cookie
        
        ydl_options = {'outtmpl': os.path.join(ArchivingContext.get_tmp_dir(), f'%(id)s.%(ext)s'), 'quiet': False, 'noplaylist': not self.allow_playlist , 'writesubtitles': self.subtitles, 'writeautomaticsub': self.subtitles, "live_from_start": self.live_from_start, "proxy": self.proxy, "max_downloads": self.max_downloads, "playlistend": self.max_downloads}

        if item.netloc in ['youtube.com', 'www.youtube.com']:
            if self.cookies_from_browser:
                logger.debug(f'Extracting cookies from browser {self.cookies_from_browser} for Youtube')
                ydl_options['cookiesfrombrowser'] = (self.cookies_from_browser,)
            elif self.cookie_file:
                logger.debug(f'Using cookies from file {self.cookie_file}')
                ydl_options['cookiefile'] = self.cookie_file

        ydl = yt_dlp.YoutubeDL(ydl_options) # allsubtitles and subtitleslangs not working as expected, so default lang is always "en"

        try:
            # don't download since it can be a live stream
            info = ydl.extract_info(url, download=False)
            if info.get('is_live', False) and not self.livestreams:
                logger.warning("Livestream detected, skipping due to 'livestreams' configuration setting")
                return False
        except yt_dlp.utils.DownloadError as e:
            logger.debug(f'No video - Youtube normal control flow: {e}')
            return False
        except Exception as e:
            logger.debug(f'ytdlp exception which is normal for example a facebook page with images only will cause a IndexError: list index out of range. Exception is: \n  {e}')
            return False

        # this time download
        ydl = yt_dlp.YoutubeDL({**ydl_options, "getcomments": self.comments})
        #TODO: for playlist or long lists of videos, how to download one at a time so they can be stored before the next one is downloaded?
        info = ydl.extract_info(url, download=True)

        if "entries" in info:
            entries = info.get("entries", [])
            if not len(entries):
                logger.warning('YoutubeDLArchiver could not find any video')
                return False
        else: entries = [info]

        result = Metadata()
        result.set_title(info.get("title"))
        if "description" in info: result.set_content(info["description"])
        for entry in entries:
            try:
                filename = ydl.prepare_filename(entry)
                if not os.path.exists(filename):
                    filename = filename.split('.')[0] + '.mkv'

                new_media = Media(filename)
                for x in ["duration", "original_url", "fulltitle", "description", "upload_date"]:
                    if x in entry: new_media.set(x, entry[x])

                # read text from subtitles if enabled
                if self.subtitles:
                    for lang, val in (info.get('requested_subtitles') or {}).items():
                        try:    
                            subs = pysubs2.load(val.get('filepath'), encoding="utf-8")
                            text = " ".join([line.text for line in subs])
                            new_media.set(f"subtitles_{lang}", text)
                        except Exception as e:
                            logger.error(f"Error loading subtitle file {val.get('filepath')}: {e}")
                result.add_media(new_media)
            except Exception as e:
                logger.error(f"Error processing entry {entry}: {e}")

        # extract comments if enabled
        if self.comments:
            result.set("comments", [{
                "text": c["text"],
                "author": c["author"], 
                "timestamp": datetime.datetime.fromtimestamp(c.get("timestamp"), tz = datetime.timezone.utc)
            } for c in info.get("comments", [])])

        if (timestamp := info.get("timestamp")):
            #TODO: fix deprecated timestamp, 
            timestamp = datetime.datetime.fromtimestamp(timestamp, tz = datetime.timezone.utc).isoformat()
            result.set_timestamp(timestamp)
        if (upload_date := info.get("upload_date")):
            upload_date = datetime.datetime.strptime(upload_date, '%Y%m%d').replace(tzinfo=datetime.timezone.utc)
            result.set("upload_date", upload_date)

        if self.end_means_success: result.success("yt-dlp")
        else: result.status = "yt-dlp"
        return result
