from snscrape.modules.twitter import TwitterTweetScraper, Video, Gif, Photo
from loguru import logger
from urllib.parse import urlparse

from .base_archiver import Archiver, ArchiveResult


class TwitterArchiver(Archiver):
    name = "twitter"

    def download(self, url, check_if_exists=False, filenumber=None):
        
        if 'twitter.com' != self.get_netloc(url):
            return False

        tweet_id = urlparse(url).path.split('/')
        if 'status' in tweet_id:
            i = tweet_id.index('status')
            tweet_id = tweet_id[i+1]
        else:
            return False

        scr = TwitterTweetScraper(tweet_id)

        try:
            tweet = next(scr.get_items())
        except Exception as ex:
            template = "TwitterArchiver cant get tweet and threw, which can happen if a media sensitive tweet. \n type: {0} occurred. \n arguments:{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            logger.warning(message)
            return False

        if tweet.media is None:
            logger.trace(f'No media found')
            return False

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

        page_cdn, page_hash, thumbnail = self.generate_media_page(urls, url, tweet.json(), filenumber)

        screenshot = self.get_screenshot(url, filenumber)

        return ArchiveResult(status="success", cdn_url=page_cdn, screenshot=screenshot, hash=page_hash, thumbnail=thumbnail, timestamp=tweet.date)
