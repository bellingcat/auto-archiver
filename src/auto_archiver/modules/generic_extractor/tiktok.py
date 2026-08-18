import re
import requests
from auto_archiver.utils.custom_logger import logger

from yt_dlp.extractor.tiktok import TikTokIE, TikTokLiveIE, TikTokVMIE, TikTokUserIE

from auto_archiver.core import Metadata, Media
from datetime import datetime, timezone
from .dropin import GenericDropin


class Tiktok(GenericDropin):
    """
    TikTok dropin for the Generic Extractor that uses an unofficial API if/when ytdlp fails.
    It's useful for capturing content that requires a login, like sensitive content.
    """

    # Regex pattern to match TikTok photo post URLs
    PHOTO_URL_REGEX = r"https?://(?:www\.)?tiktok\.com/@[\w\.-]+/photo/\d+"
    TIKWM_ENDPOINT = "https://www.tikwm.com/api/?url={url}"

    def suitable(self, url, info_extractor) -> bool:
        """This dropin (which uses Tikvm) is suitable for *all* Tiktok type URLs - videos, lives, VMs, and users.
        Return the 'suitable' method from the TikTokIE class."""
        return any(extractor().suitable(url) for extractor in (TikTokIE, TikTokLiveIE, TikTokVMIE, TikTokUserIE)) or (
            re.match(self.PHOTO_URL_REGEX, url) is not None
        )

    def extract_post(self, url: str, ie_instance):
        logger.debug("Using Tikwm API to attempt to download tiktok video")

        endpoint = self.TIKWM_ENDPOINT.format(url=url)

        r = requests.get(endpoint)
        if r.status_code != 200:
            raise ValueError(f"Unexpected status code '{r.status_code}' from tikwm.com")

        try:
            json_response = r.json()
        except ValueError:
            raise ValueError("Failed to parse JSON response from tikwm.com")

        if not json_response.get("msg") == "success" or not (api_data := json_response.get("data", {})):
            raise ValueError(f"Unable to download with tikwm.com: {repr(json_response)}")

        # tries to get the non-watermarked version first
        play_url = api_data.pop("play", api_data.pop("wmplay", None))
        if play_url and "mime_type=audio" in play_url:
            play_url = None
        if play_url:
            api_data["video_url"] = play_url
        return api_data

    def keys_to_clean(self, video_data: dict, info_extractor):
        return [
            "video_url",
            "title",
            "create_time",
            "author",
            "cover",
            "origin_cover",
            "ai_dynamic_cover",
            "duration",
            "size",
            "wm_size",
            "music",
            "music_info",
            "play_count",
            "digg_count",
            "comment_count",
            "share_count",
            "download_count",
            "collect_count",
            "anchors",
            "anchors_extras",
            "is_ad",
            "commerce_info",
            "commercial_video_info",
            "item_comment_settings",
            "mentioned_users",
        ]  # all of these will be added via api_data in a single metadata field vs individual ones in the generic extractor

    def create_metadata(self, post: dict, ie_instance, archiver, url):
        # prepare result, start by downloading video
        result = Metadata()
        is_success = False
        # get the cover if possible
        cover_url = post.pop("origin_cover", post.pop("cover", post.pop("ai_dynamic_cover", None)))
        if cover_url and (cover_downloaded := archiver.download_from_url(cover_url)):
            result.add_media(Media(cover_downloaded))

        for image_url in post.pop("images", []):
            if image_downloaded := archiver.download_from_url(image_url):
                result.add_media(Media(image_downloaded))
                is_success = True  # this is an images post and we got it/them

        # get the video if present, could be an image post
        if video_url := post.pop("video_url", None):
            video_downloaded = archiver.download_from_url(video_url, f"vid_{post.get('id', '')}")
            if not video_downloaded:
                logger.error("Failed to download video")
                return False
            video_media = Media(video_downloaded)
            if duration := post.pop("duration", None):
                video_media.set("duration", duration)
            result.add_media(video_media)
            is_success = True  # this is a video post and we got it

        # add remaining metadata
        result.set_title(post.pop("title", ""))

        if created_at := post.pop("create_time", None):
            result.set_timestamp(datetime.fromtimestamp(created_at, tz=timezone.utc))

        if author := post.pop("author", None):
            result.set("author", author)

        result.set("api_data", {k: v for k, v in post.items() if v})
        if is_success:
            result.success("yt-dlp_TikTok")
        else:
            raise ValueError("Unable to download any media from TikTok post, possibly deleted or private.")
        return result
