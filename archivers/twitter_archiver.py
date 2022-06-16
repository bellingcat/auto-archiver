
import html
from urllib.parse import urlparse
from loguru import logger
from snscrape.modules.twitter import TwitterTweetScraper, Video, Gif, Photo

from .base_archiver import Archiver, ArchiveResult


class TwitterArchiver(Archiver):
    name = "twitter"

    def download(self, url, check_if_exists=False):

        if 'twitter.com' != self.get_netloc(url):
            logger.debug(f'{url=} is not from twitter')
            return False

        tweet_id = urlparse(url).path.split('/')
        if 'status' in tweet_id:
            i = tweet_id.index('status')
            tweet_id = tweet_id[i + 1]
        else:
            logger.debug(f'{url=} does not contain "status"')
            return False

        scr = TwitterTweetScraper(tweet_id)

        try:
            tweet = next(scr.get_items())
        except Exception as ex:
            logger.warning(f"can't get tweet: {type(ex).__name__} occurred. args: {ex.args}")
            return False

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
