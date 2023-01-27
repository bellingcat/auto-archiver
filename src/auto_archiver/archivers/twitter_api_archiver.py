
import json, mimetypes
from datetime import datetime
from loguru import logger
from pytwitter import Api
from slugify import slugify

from . import Archiver
from .twitter_archiver import TwitterArchiver
from ..core import Metadata,Media


class TwitterApiArchiver(TwitterArchiver, Archiver):
    name = "twitter_api_archiver"

    def __init__(self, config: dict) -> None:
        super().__init__(config)

        if self.bearer_token:
            self.assert_valid_string("bearer_token")
            self.api = Api(bearer_token=self.bearer_token)
        elif self.consumer_key and self.consumer_secret and self.access_token and self.access_secret:
            self.assert_valid_string("consumer_key")
            self.assert_valid_string("consumer_secret")
            self.assert_valid_string("access_token")
            self.assert_valid_string("access_secret")
            self.api = Api(
                consumer_key=self.consumer_key, consumer_secret=self.consumer_secret, access_token=self.access_token, access_secret=self.access_secret)
        assert hasattr(self, "api") and self.api is not None, "Missing Twitter API configurations, please provide either bearer_token OR (consumer_key, consumer_secret, access_token, access_secret) to use this archiver."

    @staticmethod
    def configs() -> dict:
        return {
            "bearer_token": {"default": None, "help": "twitter API bearer_token which is enough for archiving, if not provided you will need consumer_key, consumer_secret, access_token, access_secret"},
            "consumer_key": {"default": None, "help": "twitter API consumer_key"},
            "consumer_secret": {"default": None, "help": "twitter API consumer_secret"},
            "access_token": {"default": None, "help": "twitter API access_token"},
            "access_secret": {"default": None, "help": "twitter API access_secret"},
        }

    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()
        # detect URLs that we definitely cannot handle
        username, tweet_id = self.get_username_tweet_id(url)
        if not username: return False

        try:
            tweet = self.api.get_tweet(tweet_id, expansions=["attachments.media_keys"], media_fields=["type", "duration_ms", "url", "variants"], tweet_fields=["attachments", "author_id", "created_at", "entities", "id", "text", "possibly_sensitive"])
        except Exception as e:
            logger.error(f"Could not get tweet: {e}")
            return False

        result = Metadata()
        result.set_title(tweet.data.text)
        result.set_timestamp(datetime.strptime(tweet.data.created_at, "%Y-%m-%dT%H:%M:%S.%fZ"))

        urls = []
        if tweet.includes:
            for i, m in enumerate(tweet.includes.media):
                media = Media(filename="")
                if m.url and len(m.url):
                    media.set("src", m.url)
                    media.set("duration", (m.duration_ms or 1) // 1000)
                    mimetype = "image/jpeg"
                elif hasattr(m, "variants"):
                    variant = self.choose_variant(m.variants)
                    if not variant: continue
                    media.set("src", variant.url)
                    mimetype = variant.content_type
                else:
                    continue
                logger.info(f"Found media {media}")
                ext = mimetypes.guess_extension(mimetype)
                media.filename = self.download_from_url(media.get("src"), f'{slugify(url)}_{i}{ext}', item)
                result.add_media(media)

        result.set_content(json.dumps({
            "id": tweet.data.id,
            "text": tweet.data.text,
            "created_at": tweet.data.created_at,
            "author_id": tweet.data.author_id,
            "geo": tweet.data.geo,
            "lang": tweet.data.lang,
            "media": urls
        }, ensure_ascii=False, indent=4))
        return result.success("twitter")

    def choose_variant(self, variants):
        # choosing the highest quality possible
        variant, bit_rate = None, -1
        for var in variants:
            if var.content_type == "video/mp4":
                if var.bit_rate > bit_rate:
                    bit_rate = var.bit_rate
                    variant = var
            else:
                variant = var if not variant else variant
        return variant
