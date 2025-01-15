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
    
    def download_additional_media(self, ie: str, video_data: dict, metadata: Metadata) -> Metadata:
        """
        Downloads additional media like images, comments, subtitles, etc.

        Creates a 'media' object and attaches it to the metadata object.
        """

        # TODO: should we download all thumbnails, or just the chosen thumbnail?

        # Right now, just getting the single thumbnail
        thumbnail_url = video_data.get('thumbnail')
        if thumbnail_url:
            try:
                cover_image_path = self.download_from_url(thumbnail_url)
                media = Media(cover_image_path)
                metadata.add_media(media, id="cover")
            except Exception as e:
                logger.error(f"Error downloading cover image {thumbnail_url}: {e}")

        return metadata

    def keys_to_clean(self, ie: str, video_data: dict) -> dict:
        """
        Clean up the video data to make it more readable and remove unnecessary keys that ytdlp adds
        """

        base_keys = ['formats', 'thumbnail', 'display_id', 'epoch', 'requested_downloads',
                     'duration_string', 'thumbnails', 'http_headers', 'webpage_url_basename', 'webpage_url_domain',
                     'extractor', 'extractor_key', 'playlist', 'playlist_index', 'duration_string', 'protocol', 'requested_subtitles',
                     'format_id', 'acodec', 'vcodec', 'ext', 'epoch', '_has_drm', 'filesize', 'audio_ext', 'video_ext', 'vbr', 'abr',
                     'resolution', 'dynamic_range', 'aspect_ratio', 'cookies', 'format', 'quality', 'preference', 'artists',
                     'channel_id', 'subtitles', 'tbr', 'url', 'original_url', 'automatic_captions', 'playable_in_embed', 'live_status',
                     '_format_sort_fields', 'chapters', 'uploader_id', 'uploader_url', 'requested_formats', 'format_note',
                     'audio_channels', 'asr', 'fps', 'was_live', 'is_live', 'heatmap', 'age_limit', 'stretched_ratio']
        if ie == 'TikTok':
            return base_keys + []
        
        return base_keys
    
    def add_metadata(self, ie: str, video_data: dict, url:str, result: Metadata) -> Metadata:
        """
        Creates a Metadata object from the give video_data
        """

        # first add the media
        result = self.download_additional_media(ie, video_data, result)

        # keep the full title, no need for the shortened title (?)
        video_data['title'] = video_data.pop('fulltitle', video_data.get('title'))
        result.set_title(video_data.pop('title', url))

        # then add the platform specific additional metadata
        for key, mapping in self.video_data_metadata_mapping(ie, video_data).items():
            if isinstance(mapping, str):
                result.set(key, eval(f"video_data{mapping}"))
            elif callable(mapping):
                result.set(key, mapping(video_data))
        result.set_url(url)

        # extract comments if enabled
        if self.comments:
            result.set("comments", [{
                "text": c["text"],
                "author": c["author"], 
                "timestamp": datetime.datetime.fromtimestamp(c.get("timestamp"), tz = datetime.timezone.utc)
            } for c in video_data.get("comments", [])])

        # then add the common metadata
        if (timestamp := video_data.pop("timestamp", None)):
            timestamp = datetime.datetime.fromtimestamp(timestamp, tz = datetime.timezone.utc).isoformat()
            result.set_timestamp(timestamp)
        if (upload_date := video_data.pop("upload_date", None)):
            upload_date = datetime.datetime.strptime(upload_date, '%Y%m%d').replace(tzinfo=datetime.timezone.utc)
            result.set("upload_date", upload_date)
        
        # then clean away any keys we don't want
        for clean_key in self.keys_to_clean(ie, video_data):
            video_data.pop(clean_key, None)
        
        # then add the rest of the video data
        for k, v in video_data.items():
            if v:
                result.set(k, v)

        return result

    def video_data_metadata_mapping(self, ie: str, video_data: dict) -> dict:
        """
        Returns a key->value mapping to map from the yt-dlp produced 'video_data' to the Metadata object.
        Can be either a string for direct mapping, or a function, or a lambda.
        """
        return {}

    def suitable(self, item: Metadata) -> bool:
        """
        Checks for valid URLs out of all ytdlp extractors.
        Returns False for the GenericIE, which as labelled by yt-dlp: 'Generic downloader that works on some sites'
        """
        url = item.get_url()
        for ie_key, ie in yt_dlp.YoutubeDL()._ies.items():
            # Note: this will return True for *all* URLs due to the 'generic' extractor from ytdlp (valid for all URLs).
            # should we check for the 'GenericIE' extractor and return False?
            # if ie.IE_NAME == 'generic'... - leaving it in for now, since we also want the ability to download from generic sites
            # perhaps one solution is to return 'False' initially, and then if no other installed archivers work, we try again using the generic one
            if ie.suitable(url) and ie.working():
                return True
        return False
    
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

        ie = info['extractor_key']
        result = Metadata()

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

        result = self.add_metadata(ie, info, url, result)
        extractor_name = "yt-dlp"
        if ie:
            extractor_name += f"--{ie}IE"

        if self.end_means_success: result.success(extractor_name)
        else: result.status = extractor_name
        return result
