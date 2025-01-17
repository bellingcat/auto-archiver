import os
import mimetypes

import requests
from loguru import logger

from auto_archiver.core.context import ArchivingContext
from auto_archiver.archivers.archiver import Archiver
from auto_archiver.core.metadata import Metadata, Media


def create_metadata(post: dict, archiver: Archiver, url: str) -> Metadata:
    result = Metadata()
    result.set_url(url)
    result.set_title(post["record"]["text"])
    result.set_timestamp(post["record"]["createdAt"])
    for k, v in _get_post_data(post).items():
        if v: result.set(k, v)

    # download if embeds present (1 video XOR >=1 images)
    for media in _download_bsky_embeds(post):
        result.add_media(media)
    logger.debug(f"Downloaded {len(result.media)} media files")

    return result

def _download_bsky_embeds(post: dict) -> list[Media]:
    """
    Iterates over image(s) or video in a Bluesky post and downloads them        
    """
    media = []
    embed = post.get("record", {}).get("embed", {})
    image_medias = embed.get("images", []) + embed.get("media", {}).get("images", [])
    video_medias = [e for e in [embed.get("video"), embed.get("media", {}).get("video")] if e]

    for image_media in image_medias:
        image_media = _download_bsky_file_as_media(image_media["image"]["ref"]["$link"], post["author"]["did"])
        media.append(image_media)
    for video_media in video_medias:
        video_media = _download_bsky_file_as_media(video_media["ref"]["$link"], post["author"]["did"])
        media.append(video_media)
    return media

def _download_bsky_file_as_media(cid: str, did: str) -> Media:
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

def _get_post_data(post: dict) -> dict:
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