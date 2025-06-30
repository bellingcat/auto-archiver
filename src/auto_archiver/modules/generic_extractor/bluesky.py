from auto_archiver.utils.custom_logger import logger

from auto_archiver.core.extractor import Extractor
from auto_archiver.core.metadata import Metadata, Media
from .dropin import GenericDropin, InfoExtractor


class Bluesky(GenericDropin):
    def create_metadata(self, post: dict, ie_instance: InfoExtractor, archiver: Extractor, url: str) -> Metadata:
        result = Metadata()
        result.set_url(url)
        result.set_title(post["record"]["text"])
        result.set_timestamp(post["record"]["createdAt"])
        for k, v in self._get_post_data(post).items():
            if v:
                result.set(k, v)

        # download if embeds present (1 video XOR >=1 images)
        for media in self._download_bsky_embeds(post, archiver):
            result.add_media(media)
        logger.debug(f"Downloaded {len(result.media)} media files")

        return result

    def extract_post(self, url: str, ie_instance: InfoExtractor) -> dict:
        # TODO: If/when this PR (https://github.com/yt-dlp/yt-dlp/pull/12098) is merged on ytdlp, remove the comments and delete the code below
        handle, video_id = ie_instance._match_valid_url(url).group("handle", "id")
        return ie_instance._extract_post(handle=handle, post_id=video_id)

    def _download_bsky_embeds(self, post: dict, archiver: Extractor) -> list[Media]:
        """
        Iterates over image(s) or video in a Bluesky post and downloads them
        """
        media = []
        embed = post.get("record", {}).get("embed", {})
        image_medias = embed.get("images", []) + embed.get("media", {}).get("images", [])
        video_medias = [e for e in [embed.get("video"), embed.get("media", {}).get("video")] if e]

        media_url = "https://bsky.social/xrpc/com.atproto.sync.getBlob?cid={}&did={}"
        for image_media in image_medias:
            url = media_url.format(image_media["image"]["ref"]["$link"], post["author"]["did"])
            image_media = archiver.download_from_url(url)
            media.append(Media(image_media))
        for video_media in video_medias:
            url = media_url.format(video_media["ref"]["$link"], post["author"]["did"])
            video_media = archiver.download_from_url(url)
            media.append(Media(video_media))
        return media

    def _get_post_data(self, post: dict) -> dict:
        """
        Extracts relevant information returned by the .getPostThread api call (excluding text/created_at): author, mentions, tags, links.
        """
        author = post["author"]
        if "labels" in author and not author["labels"]:
            del author["labels"]
        if "associated" in author:
            del author["associated"]

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
        if mentions:
            res["mentions"] = mentions
        if tags:
            res["tags"] = tags
        if links:
            res["links"] = links
        return res
