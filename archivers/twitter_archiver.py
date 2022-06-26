import html, re, requests
from datetime import datetime
from loguru import logger
from snscrape.modules.twitter import TwitterTweetScraper, Video, Gif, Photo

from .base_archiver import Archiver, ArchiveResult


class TwitterArchiver(Archiver):
    name = "twitter"
    link_pattern = re.compile(r"twitter.com\/(?:\#!\/)?(\w+)\/status(?:es)?\/(\d+)")

    def get_username_tweet_id(self, url):
        # detect URLs that we definitely cannot handle
        matches = self.link_pattern.findall(url)
        if not len(matches): return False, False

        username, tweet_id = matches[0]  # only one URL supported
        logger.debug(f"Found {username=} and {tweet_id=} in {url=}")

        return username, tweet_id

    def download(self, url, check_if_exists=False):
        username, tweet_id = self.get_username_tweet_id(url)
        if not username: return False

        scr = TwitterTweetScraper(tweet_id)

        try:
            tweet = next(scr.get_items())
        except Exception as ex:
            logger.warning(f"can't get tweet: {type(ex).__name__} occurred. args: {ex.args}")
            return self.download_alternative(url, tweet_id)

        if tweet.media is None:
            logger.debug(f'No media found, archiving tweet text only')
            screenshot = self.get_screenshot(url)
            page_cdn, page_hash, _ = self.generate_media_page_html(url, [], html.escape(tweet.json()))
            return ArchiveResult(status="success", cdn_url=page_cdn, title=tweet.content, timestamp=tweet.date, hash=page_hash, screenshot=screenshot)

        urls = []

        for media in tweet.media:
            if type(media) == Video:
                variant = max(
                    [v for v in media.variants if v.bitrate], key=lambda v: v.bitrate)
                urls.append(variant.url)
            elif type(media) == Gif:
                urls.append(media.variants[0].url)
            elif type(media) == Photo:
                urls.append(media.fullUrl.replace('name=large', 'name=orig'))
            else:
                logger.warning(f"Could not get media URL of {media}")

        page_cdn, page_hash, thumbnail = self.generate_media_page(urls, url, tweet.json())

        screenshot = self.get_screenshot(url)

        return ArchiveResult(status="success", cdn_url=page_cdn, screenshot=screenshot, hash=page_hash, thumbnail=thumbnail, timestamp=tweet.date, title=tweet.content)

    def download_alternative(self, url, tweet_id):
        # https://stackoverflow.com/a/71867055/6196010
        logger.debug(f"Trying twitter hack for {url=}")
        hack_url = f"https://cdn.syndication.twimg.com/tweet?id={tweet_id}"
        r = requests.get(hack_url)
        if r.status_code != 200: return False
        tweet = r.json()

        urls = []
        for p in tweet["photos"]:
            urls.append(p["url"])

        # 1 tweet has 1 video max
        v = tweet["video"]
        urls.append(self.choose_variant(v.get("variants", [])))

        logger.debug(f"Twitter hack got {urls=}")

        timestamp = datetime.strptime(tweet["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
        screenshot = self.get_screenshot(url)
        page_cdn, page_hash, thumbnail = self.generate_media_page(urls, url, r.text)
        return ArchiveResult(status="success", cdn_url=page_cdn, screenshot=screenshot, hash=page_hash, thumbnail=thumbnail, timestamp=timestamp, title=tweet["text"])

    def choose_variant(self, variants):
        # choosing the highest quality possible
        variant, width, height = None, 0, 0
        for var in variants:
            if var["type"] == "video/mp4":
                width_height = re.search(r"\/(\d+)x(\d+)\/", var["src"])
                if width_height:
                    w, h = int(width_height[1]), int(width_height[2])
                    if w > width or h > height:
                        width, height = w, h
                        variant = var.get("src", variant)
            else:
                variant = var.get("src") if not variant else variant
        return variant
