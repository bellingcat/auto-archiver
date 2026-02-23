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
from bs4 import BeautifulSoup
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
        except Exception:
            # try nitter
            nitter_url = f"https://nitter.net/i/status/{twid}"
            # nitter_url = f"https://nitter.space/i/status/{twid}"
            logger.info(f"Falling back to nitter.net for tweet extraction at {nitter_url}")

            @retry(wait_random_min=500, wait_random_max=2000, stop_max_attempt_number=3)
            def fetch_nitter_soup(url):
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0"
                }
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code != 200:
                    raise ValueError("Failed to retrieve tweet from nitter.net")
                logger.error(resp.text)
                soup = BeautifulSoup(resp.text, "html.parser")
                tweet_container = soup.find("div", {"class": "main-tweet"})
                if not tweet_container:
                    raise ValueError("Could not find tweet container on nitter.net page")
                return tweet_container

            tweet_container = fetch_nitter_soup(nitter_url)
            user = tweet_container.find("a", {"class": "username"})
            author = user.text.strip() if user else ""
            created_at = tweet_container.find("span", {"class": "tweet-date"})
            timestamp = created_at.find("a")["title"] if created_at and created_at.find("a") else ""

            full_text = tweet_container.find("div", {"class": "tweet-content"})
            text = full_text.text.strip() if full_text else ""

            media = []
            media_tags = tweet_container.find_all("a", {"class": "still-image"})
            for m in media_tags:
                img_url = m["href"]
                if img_url.startswith("/"):
                    img_url = "https://nitter.net" + img_url
                media.append({"type": "photo", "media_url_https": img_url})

            video_tags = tweet_container.find_all("video")
            for v in video_tags:
                src = v.find("source")
                if src and src.get("src"):
                    video_url = src["src"]
                    if video_url.startswith("/"):
                        video_url = "https://nitter.net" + video_url
                    media.append(
                        {"type": "video", "video_info": {"variants": [{"url": video_url, "content_type": "video/mp4"}]}}
                    )

            return {"user": {"name": author}, "created_at": timestamp, "full_text": text, "entities": {"media": media}}

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
