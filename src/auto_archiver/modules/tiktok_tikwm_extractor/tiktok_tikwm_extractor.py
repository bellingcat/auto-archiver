import re
import requests
from loguru import logger
from datetime import datetime, timezone
from yt_dlp.extractor.tiktok import TikTokIE

from auto_archiver.core import Extractor
from auto_archiver.core import Metadata, Media


class TiktokTikwmExtractor(Extractor):
    """
    Extractor for TikTok that uses an unofficial API and can capture content that requires a login, like sensitive content.
    """
    TIKWM_ENDPOINT = "https://www.tikwm.com/api/?url={url}"

    def download(self, item: Metadata) -> bool | Metadata:
        url = item.get_url()
        
        if not re.match(TikTokIE._VALID_URL, url):
            return False

        endpoint = TiktokTikwmExtractor.TIKWM_ENDPOINT.format(url=url)

        r = requests.get(endpoint)
        if r.status_code != 200:
            logger.error(f"unexpected status code '{r.status_code}' from tikwm.com for {url=}:")
            return False

        try:
            json_response = r.json()
        except ValueError:
            logger.error(f"failed to parse JSON response from tikwm.com for {url=}")
            return False

        if not json_response.get('msg') == 'success' or not (api_data := json_response.get('data', {})):
            logger.error(f"failed to get a valid response from tikwm.com for {url=}: {json_response}")
            return False

        # tries to get the non-watermarked version first
        video_url = api_data.pop("play", api_data.pop("wmplay", None))
        if not video_url:
            logger.error(f"no valid video URL found in response from tikwm.com for {url=}")
            return False

        # prepare result, start by downloading video
        result = Metadata()

        # get the cover if possible
        cover_url = api_data.pop("origin_cover", api_data.pop("cover", api_data.pop("ai_dynamic_cover", None)))
        if cover_url and (cover_downloaded := self.download_from_url(cover_url)):
            result.add_media(Media(cover_downloaded))

        # get the video or fail
        video_downloaded = self.download_from_url(video_url, f"vid_{api_data.get('id', '')}")
        if not video_downloaded:
            logger.error(f"failed to download video from {video_url}")
            return False
        video_media = Media(video_downloaded)
        if duration := api_data.pop("duration", None):
            video_media.set("duration", duration)
        result.add_media(video_media)

        # add remaining metadata
        result.set_title(api_data.pop("title", ""))

        if created_at := api_data.pop("create_time", None):
            result.set_timestamp(datetime.fromtimestamp(created_at, tz=timezone.utc))

        if (author := api_data.pop("author", None)):
            result.set("author", author)

        result.set("api_data", api_data)

        return result.success("tikwm")
