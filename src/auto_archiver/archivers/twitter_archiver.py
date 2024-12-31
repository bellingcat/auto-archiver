import re, requests, mimetypes, json
from typing import Union
from datetime import datetime
from loguru import logger
from snscrape.modules.twitter import TwitterTweetScraper, Video, Gif, Photo
from yt_dlp import YoutubeDL
from yt_dlp.extractor.twitter import TwitterIE
from slugify import slugify

from . import Archiver
from ..core import Metadata, Media
from ..utils import UrlUtil


class TwitterArchiver(Archiver):
    """
    This Twitter Archiver uses unofficial scraping methods.
    """

    name = "twitter_archiver"
    link_pattern = re.compile(r"(?:twitter|x).com\/(?:\#!\/)?(\w+)\/status(?:es)?\/(\d+)")
    link_clean_pattern = re.compile(r"(.+(?:twitter|x)\.com\/.+\/\d+)(\?)*.*")

    def __init__(self, config: dict) -> None:
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {}

    def sanitize_url(self, url: str) -> str:
        # expand URL if t.co and clean tracker GET params
        if 'https://t.co/' in url:
            try:
                r = requests.get(url, timeout=30)
                logger.debug(f'Expanded url {url} to {r.url}')
                url = r.url
            except:
                logger.error(f'Failed to expand url {url}')
        # https://twitter.com/MeCookieMonster/status/1617921633456640001?s=20&t=3d0g4ZQis7dCbSDg-mE7-w
        return self.link_clean_pattern.sub("\\1", url)

    def download(self, item: Metadata) -> Metadata:
        """
        if this url is archivable will download post info and look for other posts from the same group with media.
        can handle private/public channels
        """
        url = item.get_url()
        username, tweet_id = self.get_username_tweet_id(url)
        if not username: return False

        strategies = [self.download_yt_dlp, self.download_snscrape, self.download_syndication]
        for strategy in strategies:
            logger.debug(f"Trying {strategy.__name__} for {url=}")
            try:
                result = strategy(item, url, tweet_id)
                if result: return result
            except Exception as ex:
                logger.error(f"Failed to download {url} with {strategy.__name__}: {type(ex).__name__} occurred. args: {ex.args}")
        
        logger.warning(f"No free strategy worked for {url}")
        return False

        
    def download_snscrape(self, item: Metadata, url: str, tweet_id: str) -> Union[Metadata|bool]:
        scr = TwitterTweetScraper(tweet_id)
        try:
            tweet = next(scr.get_items())
        except Exception as ex:
            logger.warning(f"SNSCRAPE FAILED, can't get tweet: {type(ex).__name__} occurred. args: {ex.args}")
            return False
        
        result = Metadata()
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
                media.set("src", UrlUtil.twitter_best_quality_url(tweet_media.fullUrl))
                mimetype = "image/jpeg"
            else:
                logger.warning(f"Could not get media URL of {tweet_media}")
                continue
            ext = mimetypes.guess_extension(mimetype)
            media.filename = self.download_from_url(media.get("src"), f'{slugify(url)}_{i}{ext}')
            result.add_media(media)

        return result.success("twitter-snscrape")

    def download_syndication(self, item: Metadata, url: str, tweet_id: str) -> Union[Metadata|bool]:
        """
        Hack alternative working again.
        https://stackoverflow.com/a/71867055/6196010 (OUTDATED URL)
        https://github.com/JustAnotherArchivist/snscrape/issues/996#issuecomment-1615937362
        next to test: https://cdn.embedly.com/widgets/media.html?&schema=twitter&url=https://twitter.com/bellingcat/status/1674700676612386816
        """

        hack_url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}"
        r = requests.get(hack_url)
        if r.status_code != 200 or r.json()=={}: 
            logger.warning(f"SyndicationHack: Failed to get tweet information from {hack_url}.")
            return False
        
        result = Metadata()
        tweet = r.json()

        urls = []
        for p in tweet.get("photos", []):
            urls.append(p["url"])

        # 1 tweet has 1 video max
        if "video" in tweet:
            v = tweet["video"]
            urls.append(self.choose_variant(v.get("variants", []))['url'])

        logger.debug(f"Twitter hack got {urls=}")

        for i, u in enumerate(urls):
            media = Media(filename="")
            u = UrlUtil.twitter_best_quality_url(u)
            media.set("src", u)
            ext = ""
            if (mtype := mimetypes.guess_type(UrlUtil.remove_get_parameters(u))[0]):
                ext = mimetypes.guess_extension(mtype)

            media.filename = self.download_from_url(u, f'{slugify(url)}_{i}{ext}')
            result.add_media(media)

        result.set_title(tweet.get("text")).set_content(json.dumps(tweet, ensure_ascii=False)).set_timestamp(datetime.strptime(tweet["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"))
        return result.success("twitter-syndication")

    def download_yt_dlp(self, item: Metadata, url: str, tweet_id: str) -> Union[Metadata|bool]:
        downloader = YoutubeDL()
        tie = TwitterIE(downloader)
        tweet = tie._extract_status(tweet_id)
        result = Metadata()
        try:
            timestamp = datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S %z %Y")
        except Exception as ex:
            logger.warning(f"Failed to get timestamp: {type(ex).__name__} occurred. args: {ex.args}")
            return False
                
        result\
            .set_title(tweet.get('full_text', ''))\
            .set_content(json.dumps(tweet, ensure_ascii=False))\
            .set_timestamp(timestamp)
        if not tweet.get("entities", {}).get("media"):
            logger.debug('No media found, archiving tweet text only')
            result.status = "twitter-ytdl"
            return result
        for i, tw_media in enumerate(tweet["entities"]["media"]):
            media = Media(filename="")
            mimetype = ""
            if tw_media["type"] == "photo":
                media.set("src", UrlUtil.twitter_best_quality_url(tw_media['media_url_https']))
                mimetype = "image/jpeg"
            elif tw_media["type"] == "video":
                variant = self.choose_variant(tw_media['video_info']['variants'])
                media.set("src", variant['url'])
                mimetype = variant['content_type']
            elif tw_media["type"] == "animated_gif":
                variant = tw_media['video_info']['variants'][0]
                media.set("src", variant['url'])
                mimetype = variant['content_type']
            ext = mimetypes.guess_extension(mimetype)
            media.filename = self.download_from_url(media.get("src"), f'{slugify(url)}_{i}{ext}', item)
            result.add_media(media)
        return result.success("twitter-ytdl")

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
