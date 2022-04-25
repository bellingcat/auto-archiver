from snscrape.modules.twitter import TwitterTweetScraper, Video, Gif, Photo
from loguru import logger
import requests
from urllib.parse import urlparse

from .base_archiver import Archiver, ArchiveResult

import traceback


class TwitterArchiver(Archiver):
    name = "twitter"

    def download(self, url, check_if_exists=False):
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
        # except:
        except Exception as e:
            # logger.warning('wah wah')
            # DM can happen if a media sensitive tweet
            # logger.warning(f'Exception in twitter_archiver - traceback: {traceback.format_exc()}')
            logger.warning(f'TwitterArchiver cant get tweet - can happen if a media sensitive tweet', exc_info=True)
            return False

        if tweet.media is None:
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
                # https://webtrickz.com/download-images-in-original-size-on-twitter/
                # 'https://pbs.twimg.com/media/ExeUSW2UcAE6RbN?format=jpg&name=large'
                # we want name=orig
                # so can get original quality
                foo = media.fullUrl
                bar = foo.replace("name=large", "name=orig")

                # urls.append(media.fullUrl)
                urls.append(bar)
            else:
                logger.warning(f"Could not get media URL of {media}")

        page_cdn, page_hash, thumbnail = self.generate_media_page(urls, url, tweet.json())

        screenshot = self.get_screenshot(url)

        return ArchiveResult(status="success", cdn_url=page_cdn, screenshot=screenshot, hash=page_hash, thumbnail=thumbnail, timestamp=tweet.date)
