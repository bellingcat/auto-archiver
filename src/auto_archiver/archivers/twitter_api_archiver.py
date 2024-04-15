
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

        self.api_index = 0
        self.apis = []
        if len(self.bearer_tokens):
            self.apis.extend([Api(bearer_token=bearer_token) for bearer_token in self.bearer_tokens])
        if self.bearer_token:
            self.assert_valid_string("bearer_token")
            self.apis.append(Api(bearer_token=self.bearer_token))
        if self.consumer_key and self.consumer_secret and self.access_token and self.access_secret:
            self.assert_valid_string("consumer_key")
            self.assert_valid_string("consumer_secret")
            self.assert_valid_string("access_token")
            self.assert_valid_string("access_secret")
            self.apis.append(Api(consumer_key=self.consumer_key, consumer_secret=self.consumer_secret,
                             access_token=self.access_token, access_secret=self.access_secret))
        assert self.api_client is not None, "Missing Twitter API configurations, please provide either AND/OR (consumer_key, consumer_secret, access_token, access_secret) to use this archiver, you can provide both for better rate-limit results."

    @staticmethod
    def configs() -> dict:
        return {
            "bearer_token": {"default": None, "help": "[deprecated: see bearer_tokens] twitter API bearer_token which is enough for archiving, if not provided you will need consumer_key, consumer_secret, access_token, access_secret"},
            "bearer_tokens": {"default": [], "help": " a list of twitter API bearer_token which is enough for archiving, if not provided you will need consumer_key, consumer_secret, access_token, access_secret, if provided you can still add those for better rate limits. CSV of bearer tokens if provided via the command line", "cli_set": lambda cli_val, cur_val: list(set(cli_val.split(",")))},
            "consumer_key": {"default": None, "help": "twitter API consumer_key"},
            "consumer_secret": {"default": None, "help": "twitter API consumer_secret"},
            "access_token": {"default": None, "help": "twitter API access_token"},
            "access_secret": {"default": None, "help": "twitter API access_secret"},
        }
    
    @property  # getter .mimetype
    def api_client(self) -> str:
        return self.apis[self.api_index]
    

    def download(self, item: Metadata) -> Metadata:
        # call download retry until success or no more apis
        while self.api_index < len(self.apis):
            if res := self.download_retry(item): return res
            self.api_index += 1
        self.api_index = 0
        return False

    def download_retry(self, item: Metadata) -> Metadata:
        url = item.get_url()
        # detect URLs that we definitely cannot handle
        username, tweet_id = self.get_username_tweet_id(url)
        if not username: return False

        try:
            tweet = self.api_client.get_tweet(tweet_id, expansions=["attachments.media_keys"], media_fields=["type", "duration_ms", "url", "variants"], tweet_fields=["attachments", "author_id", "created_at", "entities", "id", "text", "possibly_sensitive"])
            logger.debug(tweet)
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
                media.filename = self.download_from_url(media.get("src"), f'{slugify(url)}_{i}{ext}')
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
