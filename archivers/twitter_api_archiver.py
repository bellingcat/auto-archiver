
import json
from datetime import datetime
from loguru import logger
from pytwitter import Api

from storages.base_storage import Storage
from configs import TwitterApiConfig
from .base_archiver import ArchiveResult
from .twitter_archiver import TwitterArchiver


class TwitterApiArchiver(TwitterArchiver):
    name = "twitter_api"

    def __init__(self, storage: Storage, driver, config: TwitterApiConfig, hash_algorithm):
        super().__init__(storage, driver, hash_algorithm)

        if config.bearer_token:
            self.api = Api(bearer_token=config.bearer_token)
        elif config.consumer_key and config.consumer_secret and config.access_token and config.access_secret:
            self.api = Api(
                consumer_key=config.consumer_key, consumer_secret=config.consumer_secret, access_token=config.access_token, access_secret=config.access_secret)

    def download(self, url, check_if_exists=False):
        if not hasattr(self, "api"):
            logger.warning('Missing Twitter API config')
            return False

        username, tweet_id = self.get_username_tweet_id(url)
        if not username: return False

        tweet = self.api.get_tweet(tweet_id, expansions=["attachments.media_keys"], media_fields=["type", "duration_ms", "url", "variants"], tweet_fields=["attachments", "author_id", "created_at", "entities", "id", "text", "possibly_sensitive"])
        timestamp = datetime.strptime(tweet.data.created_at, "%Y-%m-%dT%H:%M:%S.%fZ")

        # check if exists
        key = self.get_html_key(url)
        if check_if_exists and self.storage.exists(key):
            # only s3 storage supports storage.exists as not implemented on gd
            cdn_url = self.storage.get_cdn_url(key)
            screenshot = self.get_screenshot(url)
            return ArchiveResult(status='already archived', cdn_url=cdn_url, title=tweet.data.text, timestamp=timestamp, screenshot=screenshot)

        urls = []
        if tweet.includes:
            for m in tweet.includes.media:
                if m.url:
                    urls.append(m.url)
                elif hasattr(m, "variants"):
                    var_url = self.choose_variant(m.variants)
                    urls.append(var_url)
                else:
                    urls.append(None)  # will trigger error

            for u in urls:
                if u is None:
                    logger.debug(f"Should not have gotten None url for {tweet.includes.media=} so going to download_alternative in twitter_archiver")
                    return self.download_alternative(url, tweet_id)
        logger.debug(f"found {urls=}")

        output = json.dumps({
            "id": tweet.data.id,
            "text": tweet.data.text,
            "created_at": tweet.data.created_at,
            "author_id": tweet.data.author_id,
            "geo": tweet.data.geo,
            "lang": tweet.data.lang,
            "media": urls
        }, ensure_ascii=False, indent=4)

        screenshot = self.get_screenshot(url)
        page_cdn, page_hash, thumbnail = self.generate_media_page(urls, url, output)
        return ArchiveResult(status="success", cdn_url=page_cdn, screenshot=screenshot, hash=page_hash, thumbnail=thumbnail, timestamp=timestamp, title=tweet.data.text)
