import os
import re, requests, mimetypes
from loguru import logger


from . import Archiver
from ..core import Metadata, Media, ArchivingContext


class BlueskyArchiver(Archiver):
    """
    Uses an unauthenticated Bluesky API to archive posts including metadata, images and videos. Relies on `public.api.bsky.app/xrpc` and `bsky.social/xrpc`. Avoids ATProto to avoid auth.

    Some inspiration from https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/bluesky.py
    """
    name = "bluesky_archiver"
    BSKY_POST = re.compile(r"/profile/([^/]+)/post/([a-zA-Z0-9]+)")

    def __init__(self, config: dict) -> None:
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {}

    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()
        if not re.search(self.BSKY_POST, url):
            return False

        logger.debug(f"Identified a Bluesky post: {url}, archiving...")
        result = Metadata()

        # fetch post info and update result
        post = self._get_post_from_uri(url)
        logger.debug(f"Extracted post info: {post['record']['text']}")
        result.set_title(post["record"]["text"])
        result.set_timestamp(post["record"]["createdAt"])
        for k, v in self._get_post_data(post).items():
            if v: result.set(k, v)

        # download if embeds present (1 video XOR >=1 images)
        for media in self._download_bsky_embeds(post):
            result.add_media(media)
        logger.debug(f"Downloaded {len(result.media)} media files")

        return result.success("bluesky")

    def _get_post_from_uri(self, post_uri: str) -> dict:
        """
        Calls a public (no auth needed) Bluesky API to get a post from its uri, uses .getPostThread as it brings author info as well (unlike .getPost).
        """
        post_match = re.search(self.BSKY_POST, post_uri)
        username = post_match.group(1)
        post_id = post_match.group(2)
        at_uri = f'at://{username}/app.bsky.feed.post/{post_id}'
        r = requests.get(f"https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?uri={at_uri}&depth=0&parent_height=0")
        r.raise_for_status()
        thread = r.json()
        assert thread["thread"]["$type"] == "app.bsky.feed.defs#threadViewPost"
        return thread["thread"]["post"]

    def _download_bsky_embeds(self, post: dict) -> list[Media]:
        """
        Iterates over image(s) or video in a Bluesky post and downloads them        
        """
        media = []
        embed = post.get("record", {}).get("embed", {})
        if "images" in embed:
            for image in embed["images"]:
                image_media = self._download_bsky_file_as_media(image["image"]["ref"]["$link"], post["author"]["did"])
                media.append(image_media)
        if "video" in embed:
            video_media = self._download_bsky_file_as_media(embed["video"]["ref"]["$link"], post["author"]["did"])
            media.append(video_media)
        return media

    def _download_bsky_file_as_media(self, cid: str, did: str) -> Media:
        """
        Uses the Bluesky API to download a file by its `cid` and `did`.
        """
        # TODO: replace with self.download_from_url once that function has been cleaned-up
        file_url = f"https://bsky.social/xrpc/com.atproto.sync.getBlob?cid={cid}&did={did}"
        response = requests.get(file_url, stream=True)
        response.raise_for_status()
        ext = mimetypes.guess_extension(response.headers["Content-Type"])
        filename = os.path.join(ArchivingContext.get_tmp_dir(), f"{cid}{ext}")
        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        media = Media(filename=filename)
        media.set("src", file_url)
        return media

    def _get_post_data(self, post: dict) -> dict:
        """
        Extracts relevant information returned by the .getPostThread api call (excluding text/created_at): author, mentions, tags, links.
        """
        author = post["author"]
        if "labels" in author and not author["labels"]: del author["labels"]
        if "associated" in author: del author["associated"]

        mentions, tags, links = [], [], []
        facets = post.get("record", {}).get("facets", [])
        for f in facets:
            for feature in f["features"]:
                if feature["$type"] == "app.bsky.richtext.facet#mention":
                    mentions.append(feature["did"])
                elif feature["$type"] == "app.bsky.richtext.facet#tag":
                    tags.append(feature["tag"])
                elif feature["$type"] == "app.bsky.richtext.facet#link":
                    links.append(feature["uri"])
        res = {"author": author}
        if mentions: res["mentions"] = mentions
        if tags: res["tags"] = tags
        if links: res["links"] = links
        return res
