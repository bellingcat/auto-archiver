import requests
from loguru import logger
from auto_archiver.core import Metadata, Media
from datetime import datetime, timezone
from .dropin import GenericDropin

class Tiktok(GenericDropin):
    """
    TikTok droping for the Generic Extractor that uses an unofficial API if/when ytdlp fails.
    It's useful for capturing content that requires a login, like sensitive content.
    """

    TIKWM_ENDPOINT = "https://www.tikwm.com/api/?url={url}"

    def extract_post(self, url: str, ie_instance):

        logger.debug("Using Tikwm API to attempt to download tiktok video from {url=}")

        endpoint = self.TIKWM_ENDPOINT.format(url=url)

        r = requests.get(endpoint)
        if r.status_code != 200:
            raise ValueError(f"unexpected status code '{r.status_code}' from tikwm.com for {url=}:")

        try:
            json_response = r.json()
        except ValueError:
            raise ValueError(f"failed to parse JSON response from tikwm.com for {url=}")

        if not json_response.get('msg') == 'success' or not (api_data := json_response.get('data', {})):
            raise ValueError(f"failed to get a valid response from tikwm.com for {url=}: {repr(json_response)}")

        # tries to get the non-watermarked version first
        video_url = api_data.pop("play", api_data.pop("wmplay", None))
        if not video_url:
            raise ValueError(f"no valid video URL found in response from tikwm.com for {url=}")
        
        api_data['video_url'] = video_url
        return api_data

    
    def create_metadata(self, post: dict, ie_instance, archiver, url):

                # prepare result, start by downloading video
        result = Metadata()
        video_url = post.pop("video_url")

        # get the cover if possible
        cover_url = post.pop("origin_cover", post.pop("cover", post.pop("ai_dynamic_cover", None)))
        if cover_url and (cover_downloaded := archiver.download_from_url(cover_url)):
            result.add_media(Media(cover_downloaded))

        # get the video or fail
        video_downloaded = archiver.download_from_url(video_url, f"vid_{post.get('id', '')}")
        if not video_downloaded:
            logger.error(f"failed to download video from {video_url}")
            return False
        video_media = Media(video_downloaded)
        if duration := post.pop("duration", None):
            video_media.set("duration", duration)
        result.add_media(video_media)

        # add remaining metadata
        result.set_title(post.pop("title", ""))

        if created_at := post.pop("create_time", None):
            result.set_timestamp(datetime.fromtimestamp(created_at, tz=timezone.utc))

        if (author := post.pop("author", None)):
            result.set("author", author)

        result.set("api_data", post)

        return result