"""
The `instagram_api_extractor` module provides tools for archiving various types of Instagram content
using the [Instagrapi API](https://github.com/subzeroid/instagrapi).

Connects to an Instagrapi API deployment and allows for downloading Instagram user profiles,
posts, stories, highlights, and tagged content. It offers advanced configuration options for filtering
data, reducing JSON output size, and handling large profiles.

"""

import re
from datetime import datetime

import requests
from loguru import logger
from retrying import retry
from tqdm import tqdm

from auto_archiver.core import Extractor
from auto_archiver.core import Media
from auto_archiver.core import Metadata


class InstagramAPIExtractor(Extractor):
    """
    Uses an https://github.com/subzeroid/instagrapi API deployment to fetch instagram posts data

    # TODO: improvement collect aggregates of locations[0].location and mentions for all posts
    """

    valid_url = re.compile(
        r"(?:(?:http|https):\/\/)?(?:www.)?(?:instagram.com)\/(stories(?:\/highlights)?|p|reel)?\/?([^\/\?]*)\/?(\d+)?"
    )

    def setup(self) -> None:
        if self.api_endpoint[-1] == "/":
            self.api_endpoint = self.api_endpoint[:-1]

    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()

        url.replace("instagr.com", "instagram.com").replace("instagr.am", "instagram.com")
        insta_matches = self.valid_url.findall(url)
        logger.info(f"{insta_matches=}")
        if not len(insta_matches) or len(insta_matches[0]) != 3:
            return
        if len(insta_matches) > 1:
            logger.warning(f"Multiple instagram matches found in {url=}, using the first one")
            return
        g1, g2, g3 = insta_matches[0][0], insta_matches[0][1], insta_matches[0][2]
        if g1 == "":
            return self.download_profile(item, g2)
        elif g1 == "p":
            return self.download_post(item, g2, context="post")
        elif g1 == "reel":
            return self.download_post(item, g2, context="reel")
        elif g1 == "stories/highlights":
            return self.download_highlights(item, g2)
        elif g1 == "stories":
            if len(g3):
                return self.download_post(item, id=g3, context="story")
            return self.download_stories(item, g2)
        else:
            logger.warning(f"Unknown instagram regex group match {g1=} found in {url=}")
            return

    @retry(wait_random_min=1000, wait_random_max=3000, stop_max_attempt_number=5)
    def call_api(self, path: str, params: dict) -> dict:
        headers = {"accept": "application/json", "x-access-key": self.access_token}
        logger.debug(f"calling {self.api_endpoint}/{path} with {params=}")
        return requests.get(f"{self.api_endpoint}/{path}", headers=headers, params=params).json()

    def cleanup_dict(self, d: dict | list) -> dict:
        # repeats 3 times to remove nested empty values
        if not self.minimize_json_output:
            return d
        if isinstance(d, list):
            return [self.cleanup_dict(v) for v in d]
        if not isinstance(d, dict):
            return d
        return {
            k: clean_v
            for k, v in d.items()
            if (clean_v := self.cleanup_dict(v)) not in [0.0, 0, [], {}, "", None, "null"]
            and k not in ["x", "y", "width", "height"]
        }

    def download_profile(self, result: Metadata, username: str) -> Metadata:
        # download basic profile info
        url = result.get_url()
        user = self.call_api("v2/user/by/username", {"username": username}).get("user")
        assert user, f"User {username} not found"
        user = self.cleanup_dict(user)

        result.set_title(user.get("full_name", username)).set("data", user)
        if pic_url := user.get("profile_pic_url_hd", user.get("profile_pic_url")):
            filename = self.download_from_url(pic_url)
            result.add_media(Media(filename=filename), id="profile_picture")

        if self.full_profile:
            user_id = user.get("pk")
            # download all stories
            try:
                stories = self._download_stories_reusable(result, username)
                result.set("#stories", len(stories))
            except Exception as e:
                result.append("errors", f"Error downloading stories for {username}")
                logger.error(f"Error downloading stories for {username}: {e}")

            # download all posts
            try:
                self.download_all_posts(result, user_id)
            except Exception as e:
                result.append("errors", f"Error downloading posts for {username}")
                logger.error(f"Error downloading posts for {username}: {e}")

            # download all tagged
            try:
                self.download_all_tagged(result, user_id)
            except Exception as e:
                result.append("errors", f"Error downloading tagged posts for {username}")
                logger.error(f"Error downloading tagged posts for {username}: {e}")

            # download all highlights
            try:
                self.download_all_highlights(result, username, user_id)
            except Exception as e:
                result.append("errors", f"Error downloading highlights for {username}")
                logger.error(f"Error downloading highlights for {username}: {e}")

        result.set_url(url)  # reset as scrape_item modifies it
        return result.success("insta profile")

    def download_all_highlights(self, result, username, user_id):
        count_highlights = 0
        highlights = self.call_api("v1/user/highlights", {"user_id": user_id})
        for h in highlights:
            try:
                h_info = self._download_highlights_reusable(result, h.get("pk"))
                count_highlights += len(h_info.get("items", []))
            except Exception as e:
                result.append(
                    "errors",
                    f"Error downloading highlight id{h.get('pk')} for {username}",
                )
                logger.error(f"Error downloading highlight id{h.get('pk')} for {username}: {e}")
            if self.full_profile_max_posts and count_highlights >= self.full_profile_max_posts:
                logger.info(f"HIGHLIGHTS reached full_profile_max_posts={self.full_profile_max_posts}")
                break
        result.set("#highlights", count_highlights)

    def download_post(self, result: Metadata, code: str = None, id: str = None, context: str = None) -> Metadata:
        if id:
            post = self.call_api("v1/media/by/id", {"id": id})
        else:
            post = self.call_api("v1/media/by/code", {"code": code})
        assert post, f"Post {id or code} not found"

        if caption_text := post.get("caption_text"):
            result.set_title(caption_text)

        post = self.scrape_item(result, post, context)

        if post.get("taken_at"):
            result.set_timestamp(post.get("taken_at"))
        return result.success(f"insta {context or 'post'}")

    def download_highlights(self, result: Metadata, id: str) -> Metadata:
        h_info = self._download_highlights_reusable(result, id)
        items = len(h_info.get("items", []))
        del h_info["items"]
        result.set_title(h_info.get("title")).set("data", h_info).set("#reels", items)
        return result.success("insta highlights")

    def _download_highlights_reusable(self, result: Metadata, id: str) -> dict:
        full_h = self.call_api("v2/highlight/by/id", {"id": id})
        h_info = full_h.get("response", {}).get("reels", {}).get(f"highlight:{id}")
        assert h_info, f"Highlight {id} not found: {full_h=}"

        if cover_media := h_info.get("cover_media", {}).get("cropped_image_version", {}).get("url"):
            filename = self.download_from_url(cover_media)
            result.add_media(Media(filename=filename), id=f"cover_media highlight {id}")

        items = h_info.get("items", [])[::-1]  # newest to oldest
        for h in tqdm(items, desc="downloading highlights", unit="highlight"):
            try:
                self.scrape_item(result, h, "highlight")
            except Exception as e:
                result.append("errors", f"Error downloading highlight {h.get('id')}")
                logger.error(f"Error downloading highlight, skipping {h.get('id')}: {e}")

        return h_info

    def download_stories(self, result: Metadata, username: str) -> Metadata:
        now = datetime.now().strftime("%Y-%m-%d_%H-%M")
        stories = self._download_stories_reusable(result, username)
        if stories == []:
            return result.success("insta no story")
        result.set_title(f"stories {username} at {now}").set("#stories", len(stories))
        return result.success(f"insta stories {now}")

    def _download_stories_reusable(self, result: Metadata, username: str) -> list[dict]:
        stories = self.call_api("v1/user/stories/by/username", {"username": username})
        if not stories or not len(stories):
            return []
        stories = stories[::-1]  # newest to oldest

        for s in tqdm(stories, desc="downloading stories", unit="story"):
            try:
                self.scrape_item(result, s, "story")
            except Exception as e:
                result.append("errors", f"Error downloading story {s.get('id')}")
                logger.error(f"Error downloading story, skipping {s.get('id')}: {e}")
        return stories

    def download_all_posts(self, result: Metadata, user_id: str):
        end_cursor = None
        pbar = tqdm(desc="downloading posts")

        post_count = 0
        while end_cursor != "":
            posts = self.call_api("v1/user/medias/chunk", {"user_id": user_id, "end_cursor": end_cursor})
            if not posts or not isinstance(posts, list) or len(posts) != 2:
                break
            posts, end_cursor = posts[0], posts[1]
            logger.info(f"parsing {len(posts)} posts, next {end_cursor=}")

            for p in posts:
                try:
                    self.scrape_item(result, p, "post")
                except Exception as e:
                    result.append("errors", f"Error downloading post {p.get('id')}")
                    logger.error(f"Error downloading post, skipping {p.get('id')}: {e}")
                pbar.update(1)
                post_count += 1
            if self.full_profile_max_posts and post_count >= self.full_profile_max_posts:
                logger.info(f"POSTS reached full_profile_max_posts={self.full_profile_max_posts}")
                break
        result.set("#posts", post_count)

    def download_all_tagged(self, result: Metadata, user_id: str):
        next_page_id = ""
        pbar = tqdm(desc="downloading tagged posts")

        tagged_count = 0
        while next_page_id is not None:
            resp = self.call_api("v2/user/tag/medias", {"user_id": user_id, "page_id": next_page_id})
            posts = resp.get("response", {}).get("items", [])
            if not len(posts):
                break
            next_page_id = resp.get("next_page_id")

            logger.info(f"parsing {len(posts)} tagged posts, next {next_page_id=}")

            for p in posts:
                try:
                    self.scrape_item(result, p, "tagged")
                except Exception as e:
                    result.append("errors", f"Error downloading tagged post {p.get('id')}")
                    logger.error(f"Error downloading tagged post, skipping {p.get('id')}: {e}")
                pbar.update(1)
                tagged_count += 1
            if self.full_profile_max_posts and tagged_count >= self.full_profile_max_posts:
                logger.info(f"TAGS reached full_profile_max_posts={self.full_profile_max_posts}")
                break
        result.set("#tagged", tagged_count)

    ### reusable parsing utils below

    def scrape_item(self, result: Metadata, item: dict, context: str = None) -> dict:
        """
        receives a Metadata and an API dict response
        fetches the media and adds it to the Metadata
        cleans and returns the API dict
        context can be used to give specific id prefixes to media
        """
        if "clips_metadata" in item:
            if reusable_text := item.get("clips_metadata", {}).get("reusable_text_attribute_string"):
                item["clips_metadata_text"] = reusable_text
            if self.minimize_json_output:
                del item["clips_metadata"]

        if code := item.get("code") and not result.get("url"):
            result.set_url(f"https://www.instagram.com/p/{code}/")

        resources = item.get("resources", item.get("carousel_media", []))
        item, media, media_id = self.scrape_media(item, context)
        # if resources are present take the main media from the first resource
        if not media and len(resources):
            _, media, media_id = self.scrape_media(resources[0], context)
            resources = resources[1:]

        assert media, f"Image/video not found in {item=}"

        # posts with multiple items contain a resources list
        resources_metadata = Metadata()
        for r in resources:
            self.scrape_item(resources_metadata, r)
        if not resources_metadata.is_empty():
            media.set("other media", resources_metadata.media)

        result.add_media(media, id=media_id)
        return item

    def scrape_media(self, item: dict, context: str) -> tuple[dict, Media, str]:
        # remove unnecessary info
        if self.minimize_json_output:
            for k in [
                "image_versions",
                "video_versions",
                "video_dash_manifest",
                "image_versions2",
                "video_versions2",
            ]:
                if k in item:
                    del item[k]
        item = self.cleanup_dict(item)

        image_media = None
        if image_url := item.get("thumbnail_url"):
            filename = self.download_from_url(image_url, verbose=False)
            image_media = Media(filename=filename)

        # retrieve video info
        best_id = item.get("id", item.get("pk"))
        taken_at = item.get("taken_at", item.get("taken_at_ts"))
        code = item.get("code")
        caption_text = item.get("caption_text")
        if "carousel_media" in item:
            del item["carousel_media"]

        if video_url := item.get("video_url"):
            filename = self.download_from_url(video_url, verbose=False)
            video_media = Media(filename=filename)
            if taken_at:
                video_media.set("date", taken_at)
            if code:
                video_media.set("url", f"https://www.instagram.com/p/{code}")
            if caption_text:
                video_media.set("text", caption_text)
            video_media.set("preview", [image_media])
            video_media.set("data", [item])
            return item, video_media, f"{context or 'video'} {best_id}"
        elif image_media:
            if taken_at:
                image_media.set("date", taken_at)
            if code:
                image_media.set("url", f"https://www.instagram.com/p/{code}")
            if caption_text:
                image_media.set("text", caption_text)
            image_media.set("data", [item])
            return item, image_media, f"{context or 'image'} {best_id}"

        return item, None, None
