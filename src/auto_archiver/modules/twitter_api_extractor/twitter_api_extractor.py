import json
import re
import mimetypes
import requests

from loguru import logger
from pytwitter import Api
from slugify import slugify

from auto_archiver.core import Extractor
from auto_archiver.core import Metadata, Media
from auto_archiver.utils import get_datetime_from_str


class TwitterApiExtractor(Extractor):
    valid_url: re.Pattern = re.compile(r"(?:twitter|x).com\/(?:\#!\/)?(\w+)\/status(?:es)?\/(\d+)")

    def setup(self) -> None:
        self.api_index = 0
        self.apis = []
        if len(self.bearer_tokens):
            self.apis.extend([Api(bearer_token=bearer_token) for bearer_token in self.bearer_tokens])
        if self.bearer_token:
            self.apis.append(Api(bearer_token=self.bearer_token))
        if self.consumer_key and self.consumer_secret and self.access_token and self.access_secret:
            self.apis.append(
                Api(
                    consumer_key=self.consumer_key,
                    consumer_secret=self.consumer_secret,
                    access_token=self.access_token,
                    access_secret=self.access_secret,
                )
            )
        assert self.api_client is not None, (
            "Missing Twitter API configurations, please provide either AND/OR (consumer_key, consumer_secret, access_token, access_secret) to use this archiver, you can provide both for better rate-limit results."
        )

    @property  # getter .mimetype
    def api_client(self) -> str:
        return self.apis[self.api_index]

    def sanitize_url(self, url: str) -> str:
        # expand URL if t.co and clean tracker GET params
        if "https://t.co/" in url:
            try:
                r = requests.get(url, timeout=30)
                logger.debug(f"Expanded url {url} to {r.url}")
                url = r.url
            except Exception:
                logger.error(f"Failed to expand url {url}")
        return url

    def download(self, item: Metadata) -> Metadata:
        # call download retry until success or no more apis
        while self.api_index < len(self.apis):
            if res := self.download_retry(item):
                return res
            self.api_index += 1
        self.api_index = 0
        return False

    def get_username_tweet_id(self, url):
        # detect URLs that we definitely cannot handle
        matches = self.valid_url.findall(url)
        if not len(matches):
            return False, False

        username, tweet_id = matches[0]  # only one URL supported
        logger.debug(f"Found {username=} and {tweet_id=} in {url=}")

        return username, tweet_id

    def download_retry(self, item: Metadata) -> Metadata:
        url = item.get_url()
        # detect URLs that we definitely cannot handle
        username, tweet_id = self.get_username_tweet_id(url)
        if not username:
            return False

        try:
            tweet = self.api_client.get_tweet(
                tweet_id,
                expansions=["attachments.media_keys"],
                media_fields=["type", "duration_ms", "url", "variants"],
                tweet_fields=["attachments", "author_id", "created_at", "entities", "id", "text", "possibly_sensitive"],
            )
            logger.debug(tweet)
        except Exception as e:
            logger.error(f"Could not get tweet: {e}")
            return False

        result = Metadata()
        result.set_title(tweet.data.text)
        result.set_timestamp(get_datetime_from_str(tweet.data.created_at, "%Y-%m-%dT%H:%M:%S.%fZ"))

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
                    if not variant:
                        continue
                    media.set("src", variant.url)
                    mimetype = variant.content_type
                else:
                    continue
                logger.info(f"Found media {media}")
                ext = mimetypes.guess_extension(mimetype)
                media.filename = self.download_from_url(media.get("src"), f"{slugify(url)}_{i}{ext}")
                result.add_media(media)

        result.set_content(
            json.dumps(
                {
                    "id": tweet.data.id,
                    "text": tweet.data.text,
                    "created_at": tweet.data.created_at,
                    "author_id": tweet.data.author_id,
                    "geo": tweet.data.geo,
                    "lang": tweet.data.lang,
                    "media": urls,
                },
                ensure_ascii=False,
                indent=4,
            )
        )
        return result.success("twitter-api")

    def choose_variant(self, variants):
        """
        Chooses the highest quality variable possible out of a list of variants
        """
        variant, bit_rate = None, -1
        for var in variants:
            if var.content_type == "video/mp4":
                if var.bit_rate > bit_rate:
                    bit_rate = var.bit_rate
                    variant = var
            else:
                variant = var if not variant else variant
        return variant
