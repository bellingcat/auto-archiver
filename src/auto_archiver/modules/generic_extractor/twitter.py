import re
import mimetypes

from auto_archiver.utils.custom_logger import logger
from slugify import slugify

from auto_archiver.core.metadata import Metadata, Media
from auto_archiver.utils import url as UrlUtil, get_datetime_from_str
from auto_archiver.core.extractor import Extractor
from auto_archiver.utils.deletion_detection import detect_deletion, flag_as_deleted
from auto_archiver.modules.generic_extractor.dropin import GenericDropin, InfoExtractor
import requests
from retrying import retry


class Twitter(GenericDropin):
    def choose_variant(self, variants):
        # choosing the highest quality possible
        variant, width, height = None, 0, 0
        for var in variants:
            if var.get("content_type", "") == "video/mp4":
                width_height = re.search(r"\/(\d+)x(\d+)\/", var["url"])
                if width_height:
                    w, h = int(width_height[1]), int(width_height[2])
                    if w > width or h > height:
                        width, height = w, h
                        variant = var
            else:
                variant = var if not variant else variant
        return variant

    def extract_post(self, url: str, ie_instance: InfoExtractor):
        twid = ie_instance._match_valid_url(url).group("id")
        try:
            post_data = ie_instance._extract_status(twid=twid)
            if not post_data or not post_data.get("user") or not post_data.get("created_at"):
                raise ValueError("Error retrieving post with twitter dropin")
            return post_data
        except Exception as e:
            logger.debug(f"yt-dlp twitter extraction failed: {e}")
            # try fxtwitter API as fallback
            return self._fetch_fxtwitter(twid)

    def _fetch_fxtwitter(self, twid: str) -> dict:
        """Fetch tweet data from fxtwitter API and convert to expected format."""
        fxtwitter_url = f"https://api.fxtwitter.com/status/{twid}"
        logger.info(f"Falling back to fxtwitter API for tweet extraction: {fxtwitter_url}")

        @retry(wait_random_min=500, wait_random_max=2000, stop_max_attempt_number=3)
        def fetch_fxtwitter_data(url):
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0"}
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                raise ValueError(f"Failed to retrieve tweet from fxtwitter API: {resp.status_code}")
            data = resp.json()
            if "tweet" not in data:
                raise ValueError(f"No tweet data in fxtwitter response: {data.get('message', 'Unknown error')}")
            return data["tweet"]

        tweet = fetch_fxtwitter_data(fxtwitter_url)

        # Convert fxtwitter format to expected format
        author = tweet.get("author", {}).get("name", "")
        created_at = tweet.get("created_at", "")  # Format: "Sun Feb 08 18:45:00 +0000 2026"
        full_text = tweet.get("text", "") or tweet.get("raw_text", "")

        # Convert media format
        media = []
        fx_media = tweet.get("media", {})

        # Handle photos
        for photo in fx_media.get("photos", []):
            media.append({"type": "photo", "media_url_https": photo.get("url", "")})

        # Handle videos
        for video in fx_media.get("videos", []):
            variants = video.get("variants", [])
            # Convert to expected variant format
            converted_variants = []
            for var in variants:
                converted_variants.append(
                    {
                        "url": var.get("url", ""),
                        "content_type": var.get("content_type", "video/mp4"),
                        "bitrate": var.get("bitrate", 0),
                    }
                )
            if converted_variants:
                media.append({"type": "video", "video_info": {"variants": converted_variants}})

        # Handle animated gifs (fxtwitter may include these in videos)
        for item in fx_media.get("all", []):
            if item.get("type") == "gif":
                variants = item.get("variants", [])
                converted_variants = []
                for var in variants:
                    converted_variants.append(
                        {
                            "url": var.get("url", ""),
                            "content_type": var.get("content_type", "video/mp4"),
                            "bitrate": var.get("bitrate", 0),
                        }
                    )
                if converted_variants:
                    media.append({"type": "animated_gif", "video_info": {"variants": converted_variants}})

        return {
            "user": {"name": author},
            "created_at": created_at,
            "full_text": full_text,
            "entities": {"media": media},
        }

    def keys_to_clean(self, video_data, info_extractor):
        return ["user", "created_at", "entities", "favorited", "translator_type"]

    def create_metadata(self, tweet: dict, ie_instance: InfoExtractor, archiver: Extractor, url: str) -> Metadata:
        result = Metadata()
        try:
            if not tweet.get("user") or not tweet.get("created_at"):
                # Check for deletion indicators
                deletion_info = detect_deletion(
                    video_data=tweet, url=url, error_message="Missing user or created_at fields"
                )
                if deletion_info:
                    flag_as_deleted(result, deletion_info)
                    return result

                raise ValueError("Error retrieving post. Are you sure it exists?")
            timestamp = get_datetime_from_str(tweet["created_at"], "%a %b %d %H:%M:%S %z %Y")
        except (ValueError, KeyError) as ex:
            logger.warning(f"Unable to parse tweet: {str(ex)}\nRetreived tweet data: {tweet}")
            return False

        full_text = tweet.pop("full_text", "")
        author = tweet["user"].get("name", "")
        result.set("author", author).set_url(url)

        result.set_title(f"{author} - {full_text}").set_content(full_text).set_timestamp(timestamp)
        if not tweet.get("entities", {}).get("media"):
            logger.debug("No media found, archiving tweet text only")
            result.status = "twitter-ytdl"
            return result
        for i, tw_media in enumerate(tweet["entities"]["media"]):
            media = Media(filename="")
            mimetype = ""
            if tw_media["type"] == "photo":
                media.set("src", UrlUtil.twitter_best_quality_url(tw_media["media_url_https"]))
                mimetype = "image/jpeg"
            elif tw_media["type"] == "video":
                variant = self.choose_variant(tw_media["video_info"]["variants"])
                media.set("src", variant["url"])
                mimetype = variant["content_type"]
            elif tw_media["type"] == "animated_gif":
                variant = tw_media["video_info"]["variants"][0]
                media.set("src", variant["url"])
                mimetype = variant["content_type"]
            ext = mimetypes.guess_extension(mimetype)
            media.filename = archiver.download_from_url(media.get("src"), f"{slugify(url)}_{i}{ext}")
            result.add_media(media)
        return result
