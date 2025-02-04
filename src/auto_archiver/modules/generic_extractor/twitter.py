import re, mimetypes, json
from datetime import datetime

from loguru import logger
from slugify import slugify

from auto_archiver.core.metadata import Metadata, Media
from auto_archiver.utils import url as UrlUtil
from auto_archiver.core.extractor import Extractor

from .dropin import GenericDropin, InfoExtractor

class Twitter(GenericDropin):


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
    
    def extract_post(self, url: str, ie_instance: InfoExtractor):
        twid = ie_instance._match_valid_url(url).group('id')
        return ie_instance._extract_status(twid=twid)

    def create_metadata(self, tweet: dict, ie_instance: InfoExtractor, archiver: Extractor, url: str) -> Metadata:
        result = Metadata()
        try:
            if not tweet.get("user") or not tweet.get("created_at"):
                raise ValueError(f"Error retreiving post. Are you sure it exists?")
            timestamp = datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S %z %Y")
        except (ValueError, KeyError) as ex:
            logger.warning(f"Unable to parse tweet: {str(ex)}\nRetreived tweet data: {tweet}")
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
            media.filename = archiver.download_from_url(media.get("src"), f'{slugify(url)}_{i}{ext}')
            result.add_media(media)
        return result