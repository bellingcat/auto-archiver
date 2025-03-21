"""Uses the Instaloader library to download content from Instagram. This class handles both individual posts
and user profiles, downloading as much information as possible, including images, videos, text, stories,
highlights, and tagged posts. Authentication is required via username/password or a session file.

"""

import re
import os
import shutil
import instaloader
from loguru import logger

from auto_archiver.core import Extractor
from auto_archiver.core import Metadata
from auto_archiver.core import Media


class InstagramExtractor(Extractor):
    """
    Uses Instaloader to download either a post (inc images, videos, text) or as much as possible from a profile (posts, stories, highlights, ...)
    """

    # NB: post regex should be tested before profile
    valid_url = re.compile(r"(?:(?:http|https):\/\/)?(?:www.)?(?:instagram.com|instagr.am|instagr.com)\/")
    # https://regex101.com/r/MGPquX/1
    post_pattern = re.compile(r"{valid_url}(?:p|reel)\/(\w+)".format(valid_url=valid_url))
    # https://regex101.com/r/6Wbsxa/1
    profile_pattern = re.compile(r"{valid_url}(\w+)".format(valid_url=valid_url))
    # TODO: links to stories

    def setup(self) -> None:
        logger.warning("Instagram Extractor is not actively maintained, and may not work as expected.")
        logger.warning("Please consider using the Instagram Tbot Extractor or Instagram API Extractor instead.")

        self.insta = instaloader.Instaloader(
            download_geotags=True,
            download_comments=True,
            compress_json=False,
            dirname_pattern=self.download_folder,
            filename_pattern="{date_utc}_UTC_{target}__{typename}",
        )
        try:
            self.insta.load_session_from_file(self.username, self.session_file)
        except Exception:
            try:
                logger.debug("Session file failed", exc_info=True)
                logger.info("No valid session file found - Attempting login with use and password.")
                self.insta.login(self.username, self.password)
                self.insta.save_session_to_file(self.session_file)
            except Exception as e:
                logger.error(f"Failed to setup Instagram Extractor with Instagrapi. {e}")

    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()

        # detect URLs that we definitely cannot handle
        post_matches = self.post_pattern.findall(url)
        profile_matches = self.profile_pattern.findall(url)

        # return if not a valid instagram link
        if not len(post_matches) and not len(profile_matches):
            return

        result = None
        try:
            os.makedirs(self.download_folder, exist_ok=True)
            # process if post
            if len(post_matches):
                result = self.download_post(url, post_matches[0])
            # process if profile
            elif len(profile_matches):
                result = self.download_profile(url, profile_matches[0])
        except Exception as e:
            logger.error(
                f"Failed to download with instagram extractor due to: {e}, make sure your account credentials are valid."
            )
        finally:
            shutil.rmtree(self.download_folder, ignore_errors=True)
        return result

    def download_post(self, url: str, post_id: str) -> Metadata:
        logger.debug(f"Instagram {post_id=} detected in {url=}")

        post = instaloader.Post.from_shortcode(self.insta.context, post_id)
        if self.insta.download_post(post, target=post.owner_username):
            return self.process_downloads(url, post.title, post._asdict(), post.date)

    def download_profile(self, url: str, username: str) -> Metadata:
        # gets posts, posts where username is tagged, igtv postss, stories, and highlights
        logger.debug(f"Instagram {username=} detected in {url=}")

        profile = instaloader.Profile.from_username(self.insta.context, username)
        try:
            for post in profile.get_posts():
                try:
                    self.insta.download_post(post, target=f"profile_post_{post.owner_username}")
                except Exception as e:
                    logger.error(f"Failed to download post: {post.shortcode}: {e}")
        except Exception as e:
            logger.error(f"Failed profile.get_posts: {e}")

        try:
            for post in profile.get_tagged_posts():
                try:
                    self.insta.download_post(post, target=f"tagged_post_{post.owner_username}")
                except Exception as e:
                    logger.error(f"Failed to download tagged post: {post.shortcode}: {e}")
        except Exception as e:
            logger.error(f"Failed profile.get_tagged_posts: {e}")

        try:
            for post in profile.get_igtv_posts():
                try:
                    self.insta.download_post(post, target=f"igtv_post_{post.owner_username}")
                except Exception as e:
                    logger.error(f"Failed to download igtv post: {post.shortcode}: {e}")
        except Exception as e:
            logger.error(f"Failed profile.get_igtv_posts: {e}")

        try:
            for story in self.insta.get_stories([profile.userid]):
                for item in story.get_items():
                    try:
                        self.insta.download_storyitem(item, target=f"story_item_{story.owner_username}")
                    except Exception as e:
                        logger.error(f"Failed to download story item: {item}: {e}")
        except Exception as e:
            logger.error(f"Failed get_stories: {e}")

        try:
            for highlight in self.insta.get_highlights(profile.userid):
                for item in highlight.get_items():
                    try:
                        self.insta.download_storyitem(item, target=f"highlight_item_{highlight.owner_username}")
                    except Exception as e:
                        logger.error(f"Failed to download highlight item: {item}: {e}")
        except Exception as e:
            logger.error(f"Failed get_highlights: {e}")

        return self.process_downloads(url, f"@{username}", profile._asdict(), None)

    def process_downloads(self, url, title, content, date):
        result = Metadata()
        result.set_title(title).set_content(str(content)).set_timestamp(date)

        try:
            all_media = []
            for f in os.listdir(self.download_folder):
                if os.path.isfile((filename := os.path.join(self.download_folder, f))):
                    if filename[-4:] == ".txt":
                        continue
                    all_media.append(Media(filename))

            assert len(all_media) > 1, "No uploaded media found"
            all_media.sort(key=lambda m: m.filename, reverse=True)
            for m in all_media:
                result.add_media(m)

            return result.success("instagram")
        except Exception as e:
            logger.error(f"Could not fetch instagram post {url} due to: {e}")
