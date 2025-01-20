import datetime, os, yt_dlp, pysubs2
from typing import Type
from yt_dlp.extractor.common import InfoExtractor

from loguru import logger

from . import bluesky, twitter, truth
from auto_archiver.archivers.archiver import Archiver
from ...core import Metadata, Media, ArchivingContext


class GenericArchiver(Archiver):
    name = "youtubedl_archiver" #left as is for backwards compat

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
    
    def download_additional_media(self, extractor_key: str, video_data: dict, metadata: Metadata) -> Metadata:
        """
        Downloads additional media like images, comments, subtitles, etc.

        Creates a 'media' object and attaches it to the metadata object.
        """

        # Just get the main thumbnail. More thumbnails are available in
        # video_data['thumbnails'] should they be required
        thumbnail_url = video_data.get('thumbnail')
        if thumbnail_url:
            try:
                cover_image_path = self.download_from_url(thumbnail_url)
                media = Media(cover_image_path)
                metadata.add_media(media, id="cover")
            except Exception as e:
                logger.error(f"Error downloading cover image {thumbnail_url}: {e}")

        return metadata

    def keys_to_clean(self, extractor_key: str, video_data: dict) -> dict:
        """
        Clean up the video data to make it more readable and remove unnecessary keys that ytdlp adds
        """

        base_keys = ['formats', 'thumbnail', 'display_id', 'epoch', 'requested_downloads',
                     'duration_string', 'thumbnails', 'http_headers', 'webpage_url_basename', 'webpage_url_domain',
                     'extractor', 'extractor_key', 'playlist', 'playlist_index', 'duration_string', 'protocol', 'requested_subtitles',
                     'format_id', 'acodec', 'vcodec', 'ext', 'epoch', '_has_drm', 'filesize', 'audio_ext', 'video_ext', 'vbr', 'abr',
                     'resolution', 'dynamic_range', 'aspect_ratio', 'cookies', 'format', 'quality', 'preference', 'artists',
                     'channel_id', 'subtitles', 'tbr', 'url', 'original_url', 'automatic_captions', 'playable_in_embed', 'live_status',
                     '_format_sort_fields', 'chapters', 'requested_formats', 'format_note',
                     'audio_channels', 'asr', 'fps', 'was_live', 'is_live', 'heatmap', 'age_limit', 'stretched_ratio']
        if extractor_key == 'TikTok':
            # Tiktok: only has videos so a valid ytdlp `video_data` object is returned. Base keys are enough
            return base_keys + [] 
        elif extractor_key == "Bluesky":
            # bluesky API response for non video URLs is already clean, nothing to add
            return base_keys + []
        
        
        return base_keys
    
    def add_metadata(self, extractor_key: str, video_data: dict, url:str, result: Metadata) -> Metadata:
        """
        Creates a Metadata object from the give video_data
        """

        # first add the media
        result = self.download_additional_media(extractor_key, video_data, result)

        # keep both 'title' and 'fulltitle', but prefer 'title', falling back to 'fulltitle' if it doesn't exist
        result.set_title(video_data.pop('title', video_data.pop('fulltitle', "")))
        result.set_url(url)

        # extract comments if enabled
        if self.comments:
            result.set("comments", [{
                "text": c["text"],
                "author": c["author"], 
                "timestamp": datetime.datetime.fromtimestamp(c.get("timestamp"), tz = datetime.timezone.utc)
            } for c in video_data.get("comments", [])])

        # then add the common metadata
        if timestamp := video_data.pop("timestamp", None):
            timestamp = datetime.datetime.fromtimestamp(timestamp, tz = datetime.timezone.utc).isoformat()
            result.set_timestamp(timestamp)
        if upload_date := video_data.pop("upload_date", None):
            upload_date = datetime.datetime.strptime(upload_date, '%Y%m%d').replace(tzinfo=datetime.timezone.utc)
            result.set("upload_date", upload_date)
        
        # then clean away any keys we don't want
        for clean_key in self.keys_to_clean(extractor_key, video_data):
            video_data.pop(clean_key, None)
        
        # then add the rest of the video data
        for k, v in video_data.items():
            if v:
                result.set(k, v)

        return result
    
    def suitable_extractors(self, url: str) -> list[str]:
        """
        Returns a list of valid extractors for the given URL"""
        for info_extractor in yt_dlp.YoutubeDL()._ies.values():
            if info_extractor.suitable(url) and info_extractor.working():
                yield info_extractor
        
    def suitable(self, url: str) -> bool:
        """
        Checks for valid URLs out of all ytdlp extractors.
        Returns False for the GenericIE, which as labelled by yt-dlp: 'Generic downloader that works on some sites'
        """
        return any(self.suitable_extractors(url))

    def create_metadata_for_post(self, info_extractor: InfoExtractor, post_data: dict, url: str) -> Metadata:
        """
        Standardizes the output of the 'post' data from a ytdlp InfoExtractor to Metadata object.

        This is only required for platforms that don't have videos, and therefore cannot be converted into ytdlp valid 'video_data'.
        In these instances, we need to use the extractor's _extract_post (or similar) method to get the post metadata, and then convert
        it into a Metadata object via a platform-specific function.
        """
        if info_extractor.ie_key() == 'Bluesky':
            return bluesky.create_metadata(post_data, self, url)
        if info_extractor.ie_key() == 'Twitter':
            return twitter.create_metadata(post_data, self, url)
        if info_extractor.ie_key() == 'Truth':
            return truth.create_metadata(post_data, self, url)

    def get_metatdata_for_post(self, info_extractor: Type[InfoExtractor], url: str, ydl: yt_dlp.YoutubeDL) -> Metadata:
        """
        Calls into the ytdlp InfoExtract subclass to use the prive _extract_post method to get the post metadata.
        """

        ie_instance = info_extractor(downloader=ydl)
        post_data = None

        if info_extractor.ie_key() == 'Bluesky':
            # bluesky kwargs are handle, video_id
            handle, video_id = ie_instance._match_valid_url(url).group('handle', 'id')
            post_data = ie_instance._extract_post(handle=handle, post_id=video_id)
        elif info_extractor.ie_key() == 'Twitter':
            # twitter kwargs are tweet_id
            twid = ie_instance._match_valid_url(url).group('id')
            # TODO: if ytdlp PR https://github.com/yt-dlp/yt-dlp/pull/12098 is merged, change to _extract_post
            post_data = ie_instance._extract_status(twid=twid)
        elif info_extractor.ie_key() == 'Truth':
            video_id = ie_instance._match_id(url)
            truthsocial_url = f'https://truthsocial.com/api/v1/statuses/{video_id}'
            post_data = ie_instance._download_json(truthsocial_url, video_id)
        else:
            # lame attempt at trying to get data for an unknown extractor
            # TODO: test some more video platforms and see if there's any improvement to be made
            try:
                post_data = ie_instance._extract_post(url)
            except (NotImplementedError, AttributeError) as e:
                logger.debug(f"Extractor {info_extractor.ie_key()} does not support extracting post info from non-video URLs: {e}")
                return False

        return self.create_metadata_for_post(ie_instance, post_data, url)
        
    def get_metatdata_for_video(self, info: dict, info_extractor: Type[InfoExtractor], url: str, ydl: yt_dlp.YoutubeDL) -> Metadata:
        # this time download
        ydl.params['getcomments'] = self.comments
        #TODO: for playlist or long lists of videos, how to download one at a time so they can be stored before the next one is downloaded?
        info = ydl.extract_info(url, ie_key=info_extractor.ie_key(), download=True)
        if "entries" in info:
            entries = info.get("entries", [])
            if not len(entries):
                logger.warning('YoutubeDLArchiver could not find any video')
                return False
        else: entries = [info]

        extractor_key = info['extractor_key']
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

        return self.add_metadata(extractor_key, info, url, result)

    def download_for_extractor(self, info_extractor: Type[InfoExtractor], url: str, ydl: yt_dlp.YoutubeDL) -> Metadata:
        """
        Tries to download the given url using the specified extractor
        
        It first tries to use ytdlp directly to download the video. If the post is not a video, it will then try to
        use the extractor's _extract_post method to get the post metadata if possible.
        """
        # when getting info without download, we also don't need the comments
        ydl.params['getcomments'] = False
        result = False

        try:
            # don't download since it can be a live stream
            info = ydl.extract_info(url, ie_key=info_extractor.ie_key(), download=False)
            if info.get('is_live', False) and not self.livestreams:
                logger.warning("Livestream detected, skipping due to 'livestreams' configuration setting")
                return False
            # it's a valid video, that the youtubdedl can download out of the box
            result = self.get_metatdata_for_video(info, info_extractor, url, ydl)

        except Exception as e:
            logger.debug(f'Issue using "{info_extractor.IE_NAME}" extractor to download video (error: {repr(e)}), attempting to use extractor to get post data instead')
            try:
                result = self.get_metatdata_for_post(info_extractor, url, ydl)
            except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError) as post_e:
                logger.error(f'Error downloading metadata for post: {post_e}')
                return False
            except Exception as generic_e:
                logger.debug(f'Attempt to extract using ytdlp extractor "{info_extractor.IE_NAME}" failed:  \n  {repr(generic_e)}', exc_info=True)
                return False
        
        if result:
            extractor_name = "yt-dlp"
            if info_extractor:
                extractor_name += f"_{info_extractor.ie_key()}"

            if self.end_means_success:
                result.success(extractor_name)
            else:
                result.status = extractor_name

        return result

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

        for info_extractor in self.suitable_extractors(url):
            result = self.download_for_extractor(info_extractor, url, ydl)
            if result:
                return result
       

        return False
