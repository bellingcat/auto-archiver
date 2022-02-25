from snscrape.modules.twitter import TwitterTweetScraper, Video, Gif, Photo
from loguru import logger
import requests
from urllib.parse import urlparse

from .base_archiver import Archiver, ArchiveResult


class TwitterArchiver(Archiver):
    name = "twitter"

    def download(self, url, check_if_exists=False):
        if 'twitter.com' != self.get_netloc(url):
            return False

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
        }

        tweet_id = url.split('/')
        if 'status' in tweet_id:
            i = tweet_id.index('status')
            tweet_id = tweet_id[i+1]
        else:
            return False

        scr = TwitterTweetScraper(tweet_id)

        try:
            tweet = next(scr.get_items())
        except:
            logger.warning('wah wah')
            return False

        if tweet.media is None:
            return False

        archived_media = []

        for media in tweet.media:
            if type(media) == Video:
                variant = max(
                    [v for v in media.variants if v.bitrate], key=lambda v: v.bitrate)
                media_url = variant.url
            elif type(media) == Gif:
                media_url = media.variants[0].url
            elif type(media) == Photo:
                media_url = media.fullUrl
            else:
                logger.warning(f"Could not get media URL of {media}")
                media_url = None

            if media_url is not None:
                path = urlparse(media_url).path
                key = self.get_key(path.replace("/", "_"))
                if '.' not in path:
                    key += '.jpg'

                filename = 'tmp/' + key

                d = requests.get(media_url, headers=headers)
                with open(filename, 'wb') as f:
                    f.write(d.content)

                self.storage.upload(filename, key)
                hash = self.get_hash(filename)

                archived_media.append((self.storage.get_cdn_url(key), hash))

        page = f'''<html><head><title>{url}</title></head>
            <body>
            <h2>Archived media from tweet</h2>
            <h3><a href="{url}">{url}</a></h3><ul>'''

        for media in archived_media:
            page += f'''<li><a href="{media[0]}">{media[0]}</a>: {media[1]}</li>'''

        page += f"<h2>Tweet data:</h2><code>{tweet.json()}</code>"
        page += f"</body></html>"

        page_key = self.get_key(urlparse(url).path.replace("/", "_") + ".html")
        page_filename = 'tmp/' + key
        page_cdn = self.storage.get_cdn_url(page_key)

        with open(page_filename, "w") as f:
            f.write(page)

        page_hash = self.get_hash(page_filename)

        self.storage.upload(page_filename, page_key, extra_args={
                    'ACL': 'public-read', 'ContentType': 'text/html'})

        screenshot = self.get_screenshot(url)

        if (len(archived_media) > 0):
            thumbnail = archived_media[0][0]
        else:
            thumbnail = None

        return ArchiveResult(status="success", cdn_url=page_cdn, screenshot=screenshot, hash=page_hash, thumbnail=thumbnail)

