import re, os, shutil, html, traceback
import instaloader # https://instaloader.github.io/as-module.html
from loguru import logger

from .base_archiver import Archiver, ArchiveResult
from configs import Config
from storages import Storage


class InstagramArchiver(Archiver):
    """
    Uses Instaloader to download either a post (inc images, videos, text) or as much as possible from a profile (posts, stories, highlights, )
    """
    name = "instagram"
    DOWNLOAD_FOLDER = "instaloader"
    # NB: post should be tested before profile
    # https://regex101.com/r/MGPquX/1
    post_pattern = re.compile(r"(?:(?:http|https):\/\/)?(?:www.)?(?:instagram.com|instagr.am|instagr.com)\/(?:p|reel)\/(\w+)")
    # https://regex101.com/r/6Wbsxa/1
    profile_pattern = re.compile(r"(?:(?:http|https):\/\/)?(?:www.)?(?:instagram.com|instagr.am|instagr.com)\/(\w+)")

    def __init__(self, storage: Storage, config: Config):
        super().__init__(storage, config)
        self.insta = instaloader.Instaloader(download_geotags=True, download_comments=True, compress_json=False, dirname_pattern=self.DOWNLOAD_FOLDER, filename_pattern="{date_utc}_UTC_{target}__{typename}")
        if config.instagram_config:
            try:
                self.insta.load_session_from_file(config.instagram_config.username, config.instagram_config.session_file)
            except Exception as e:
                logger.error(f"Unable to login from session file: {e}\n{traceback.format_exc()}")
                try:
                    self.insta.login(config.instagram_config.username, config.instagram_config.
                    password)
                    #TODO: wait for this issue to be fixed https://github.com/instaloader/instaloader/issues/1758
                    self.insta.save_session_to_file(config.instagram_config.session_file)
                except Exception as e2:
                    logger.error(f"Unable to finish login (retrying from file): {e2}\n{traceback.format_exc()}")



    def download(self, url, check_if_exists=False):
        post_matches = self.post_pattern.findall(url)
        profile_matches = self.profile_pattern.findall(url)

        # return if not a valid instagram link
        if not len(post_matches) and not len(profile_matches):
            return

        # check if already uploaded
        key = self.get_html_key(url)
        if check_if_exists and self.storage.exists(key):
            # only s3 storage supports storage.exists as not implemented on gd
            cdn_url = self.storage.get_cdn_url(key)
            screenshot = self.get_screenshot(url)
            wacz = self.get_wacz(url)
            return ArchiveResult(status='already archived', cdn_url=cdn_url, screenshot=screenshot, wacz=wacz)

        try:
            # process if post
            if len(post_matches):
                return self.download_post(url, post_matches[0])

            # process if profile
            if len(profile_matches):
                return self.download_profile(url, profile_matches[0])
        finally:
            shutil.rmtree(self.DOWNLOAD_FOLDER, ignore_errors=True)

    def download_post(self, url, post_id):
        logger.debug(f"Instagram {post_id=} detected in {url=}")

        post = instaloader.Post.from_shortcode(self.insta.context, post_id)
        if self.insta.download_post(post, target=post.owner_username):
            return self.upload_downloaded_content(url, post.title, post._asdict(), post.date)

    def download_profile(self, url, username):
        # gets posts, posts where username is tagged, igtv postss, stories, and highlights
        logger.debug(f"Instagram {username=} detected in {url=}")

        profile = instaloader.Profile.from_username(self.insta.context, username)
        try: 
            for post in profile.get_posts():
                try: self.insta.download_post(post, target=f"profile_post_{post.owner_username}")
                except Exception as e: logger.error(f"Failed to download post: {post.shortcode}: {e}")
        except Exception as e: logger.error(f"Failed profile.get_posts: {e}") 
        
        try: 
            for post in profile.get_tagged_posts():
                try: self.insta.download_post(post, target=f"tagged_post_{post.owner_username}")
                except Exception as e: logger.error(f"Failed to download tagged post: {post.shortcode}: {e}") 
        except Exception as e: logger.error(f"Failed profile.get_tagged_posts: {e}") 
        
        try: 
            for post in profile.get_igtv_posts():
                try: self.insta.download_post(post, target=f"igtv_post_{post.owner_username}")
                except Exception as e: logger.error(f"Failed to download igtv post: {post.shortcode}: {e}") 
        except Exception as e: logger.error(f"Failed profile.get_igtv_posts: {e}") 
        
        try: 
            for story in self.insta.get_stories([profile.userid]):
                for item in story.get_items():
                    try: self.insta.download_storyitem(item, target=f"story_item_{story.owner_username}")
                    except Exception as e: logger.error(f"Failed to download story item: {item}: {e}") 
        except Exception as e: logger.error(f"Failed get_stories: {e}") 
        
        try: 
            for highlight in self.insta.get_highlights(profile.userid):
                for item in highlight.get_items():
                    try: self.insta.download_storyitem(item, target=f"highlight_item_{highlight.owner_username}")
                    except Exception as e: logger.error(f"Failed to download highlight item: {item}: {e}") 
        except Exception as e: logger.error(f"Failed get_highlights: {e}") 

        return self.upload_downloaded_content(url, f"@{username}", profile._asdict(), None)

    def upload_downloaded_content(self, url, title, content, date):
        status = "success"
        try:
            uploaded_media = []
            for f in os.listdir(self.DOWNLOAD_FOLDER):
                if os.path.isfile((filename := os.path.join(self.DOWNLOAD_FOLDER, f))):
                    key = self.get_key(filename)
                    self.storage.upload(filename, key)
                    hash = self.get_hash(filename)
                    cdn_url = self.storage.get_cdn_url(key)
                    uploaded_media.append({'cdn_url': cdn_url, 'key': key, 'hash': hash})
            assert len(uploaded_media) > 1, "No uploaded media found"

            uploaded_media.sort(key=lambda m:m["key"], reverse=True)

            page_cdn, page_hash, _ = self.generate_media_page_html(url, uploaded_media, html.escape(str(content)))
        except Exception as e:
            logger.error(f"Could not fetch instagram post {url} due to: {e}")
            status = "error"
        finally:
            shutil.rmtree(self.DOWNLOAD_FOLDER, ignore_errors=True)

        if status == "success":
            screenshot = self.get_screenshot(url)
            wacz = self.get_wacz(url)

            return ArchiveResult(status=status, cdn_url=page_cdn, title=title, timestamp=date, hash=page_hash, screenshot=screenshot, wacz=wacz)
