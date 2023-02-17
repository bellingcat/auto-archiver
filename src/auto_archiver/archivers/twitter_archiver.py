import re, requests, mimetypes, json
from datetime import datetime
from loguru import logger
from snscrape.modules.twitter import TwitterTweetScraper, Video, Gif, Photo
from slugify import slugify

from . import Archiver
from ..core import Metadata, Media


class TwitterArchiver(Archiver):
    """
    This Twitter Archiver uses unofficial scraping methods.
    """

    name = "twitter_archiver"
    link_pattern = re.compile(r"twitter.com\/(?:\#!\/)?(\w+)\/status(?:es)?\/(\d+)")
    link_clean_pattern = re.compile(r"(.+twitter\.com\/.+\/\d+)(\?)*.*")

    def __init__(self, config: dict) -> None:
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {}

    def sanitize_url(self, url: str) -> str:
        # expand URL if t.co and clean tracker GET params
        if 'https://t.co/' in url:
            try:
                r = requests.get(url)
                logger.debug(f'Expanded url {url} to {r.url}')
                url = r.url
            except:
                logger.error(f'Failed to expand url {url}')
        # https://twitter.com/MeCookieMonster/status/1617921633456640001?s=20&t=3d0g4ZQis7dCbSDg-mE7-w
        return self.link_clean_pattern.sub("\\1", url)

    def is_rearchivable(self, url: str) -> bool:
        # Twitter posts are static (for now)
        return False

    def download(self, item: Metadata) -> Metadata:
        """
        if this url is archivable will download post info and look for other posts from the same group with media.
        can handle private/public channels
        """
        url = item.get_url()
        # detect URLs that we definitely cannot handle
        username, tweet_id = self.get_username_tweet_id(url)
        if not username: return False

        result = Metadata()

        scr = TwitterTweetScraper(tweet_id)
        try:
            tweet = next(scr.get_items())
        except Exception as ex:
            logger.warning(f"can't get tweet: {type(ex).__name__} occurred. args: {ex.args}")
            return self.download_alternative(item, url, tweet_id)

        result.set_title(tweet.content).set_content(tweet.json()).set_timestamp(tweet.date)
        if tweet.media is None:
            logger.debug(f'No media found, archiving tweet text only')
            return result

        for i, tweet_media in enumerate(tweet.media):
            media = Media(filename="")
            mimetype = ""
            if type(tweet_media) == Video:
                variant = max(
                    [v for v in tweet_media.variants if v.bitrate], key=lambda v: v.bitrate)
                media.set("src", variant.url).set("duration", tweet_media.duration)
                mimetype = variant.contentType
            elif type(tweet_media) == Gif:
                variant = tweet_media.variants[0]
                media.set("src", variant.url)
                mimetype = variant.contentType
            elif type(tweet_media) == Photo:
                media.set("src", tweet_media.fullUrl.replace('name=large', 'name=orig'))
                mimetype = "image/jpeg"
            else:
                logger.warning(f"Could not get media URL of {tweet_media}")
                continue
            ext = mimetypes.guess_extension(mimetype)
            media.filename = self.download_from_url(media.get("src"), f'{slugify(url)}_{i}{ext}', item)
            result.add_media(media)

        return result.success("twitter-snscrape")

    def download_alternative(self, item: Metadata, url: str, tweet_id: str) -> Metadata:
        """
        CURRENTLY STOPPED WORKING
        """
        return False
        # https://stackoverflow.com/a/71867055/6196010
        logger.debug(f"Trying twitter hack for {url=}")
        result = Metadata()

        hack_url = f"https://cdn.syndication.twimg.com/tweet?id={tweet_id}"
        r = requests.get(hack_url)
        if r.status_code != 200: return False
        tweet = r.json()

        urls = []
        for p in tweet["photos"]:
            urls.append(p["url"])

        # 1 tweet has 1 video max
        if "video" in tweet:
            v = tweet["video"]
            urls.append(self.choose_variant(v.get("variants", [])))

        logger.debug(f"Twitter hack got {urls=}")

        for u in urls:
            media = Media()
            media.set("src", u)
            media.filename = self.download_from_url(u, f'{slugify(url)}_{i}', item)
            result.add_media(media)

        result.set_content(json.dumps(tweet, ensure_ascii=False)).set_timestamp(datetime.strptime(tweet["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"))
        return result

    def get_username_tweet_id(self, url):
        # detect URLs that we definitely cannot handle
        matches = self.link_pattern.findall(url)
        if not len(matches): return False, False

        username, tweet_id = matches[0]  # only one URL supported
        logger.debug(f"Found {username=} and {tweet_id=} in {url=}")

        return username, tweet_id

    def choose_variant(self, variants):
        # choosing the highest quality possible
        variant, width, height = None, 0, 0
        for var in variants:
            if var.get("type", "") == "video/mp4":
                width_height = re.search(r"\/(\d+)x(\d+)\/", var["src"])
                if width_height:
                    w, h = int(width_height[1]), int(width_height[2])
                    if w > width or h > height:
                        width, height = w, h
                        variant = var.get("src", variant)
            else:
                variant = var.get("src") if not variant else variant
        return variant
