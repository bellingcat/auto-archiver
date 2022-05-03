import os
import re
import html
from loguru import logger

from storages import Storage
from .base_archiver import Archiver, ArchiveResult
from telethon.sync import TelegramClient
from configs import TelegramConfig



class TelethonArchiver(Archiver):
    name = "telethon"
    link_pattern = re.compile(r"https:\/\/t\.me(\/c){0,1}\/(.+)\/(.+)")

    def __init__(self, storage: Storage, driver, config: TelegramConfig):
        super().__init__(storage, driver)
        self.client = TelegramClient("./anon", config.api_id, config.api_hash)

    def _get_media_posts_in_group(self, chat, original_post, max_amp=10):
        """
        Searches for Telegram posts that are part of the same group of uploads
        The search is conducted around the id of the original post with an amplitude
        of `max_amp` both ways
        Returns a list of [post] where each post has media and is in the same grouped_id
        """
        if original_post.grouped_id is None:
            return [original_post] if original_post.media is not None else []

        search_ids = [i for i in range(original_post.id - max_amp, original_post.id + max_amp + 1)]
        posts = self.client.get_messages(chat, ids=search_ids)
        media = []
        for post in posts:
            if post is not None and post.grouped_id == original_post.grouped_id and post.media is not None:
                media.append(post)
        return media

    def download(self, url, check_if_exists=False):
        # detect URLs that we definitely cannot handle
        matches = self.link_pattern.findall(url)
        if not len(matches):
            return False

        status = "success"
        screenshot = self.get_screenshot(url)

        with self.client.start():
            matches = list(matches[0])
            chat, post_id = matches[1], matches[2]

            post_id = int(post_id)
            try:
                post = self.client.get_messages(chat, ids=post_id)
            except ValueError as e:
                logger.warning(f'Could not fetch telegram {url} possibly it\'s private: {e}')
                return False

            media_posts = self._get_media_posts_in_group(chat, post)

            if len(media_posts) > 1:
                key = self.get_html_key(url)
                cdn_url = self.storage.get_cdn_url(key)

                if check_if_exists and self.storage.exists(key):
                    status = 'already archived'
                    return ArchiveResult(status='already archived', cdn_url=cdn_url, title=post.message, timestamp=post.date, screenshot=screenshot)

                group_id = post.grouped_id if post.grouped_id is not None else post.id
                uploaded_media = []
                message = post.message
                for mp in media_posts:
                    if len(mp.message) > len(message): message = mp.message
                    filename = self.client.download_media(mp.media, f'tmp/{chat}_{group_id}/{mp.id}')
                    key = filename.split('tmp/')[1]
                    self.storage.upload(filename, key)
                    hash = self.get_hash(filename)
                    cdn_url = self.storage.get_cdn_url(key)
                    uploaded_media.append({'cdn_url': cdn_url, 'key': key, 'hash': hash})
                    os.remove(filename)

                page_cdn, page_hash, _ = self.generate_media_page_html(url, uploaded_media, html.escape(str(post)))

                return ArchiveResult(status=status, cdn_url=page_cdn, title=post.message, timestamp=post.date, hash=page_hash, screenshot=screenshot)
            elif len(media_posts) == 1:
                key = self.get_key(f'{chat}_{post_id}')
                filename = self.client.download_media(post.media, f'tmp/{key}')
                key = filename.split('tmp/')[1].replace(" ", "")
                self.storage.upload(filename, key)
                hash = self.get_hash(filename)
                cdn_url = self.storage.get_cdn_url(key)
                key_thumb, thumb_index = self.get_thumbnails(filename, key)
                os.remove(filename)

                return ArchiveResult(status=status, cdn_url=cdn_url, title=post.message, thumbnail=key_thumb, thumbnail_index=thumb_index, timestamp=post.date, hash=hash, screenshot=screenshot)

            page_cdn, page_hash, _ = self.generate_media_page_html(url, [], html.escape(str(post)))
            return ArchiveResult(status=status, cdn_url=page_cdn, title=post.message, timestamp=post.date, hash=page_hash, screenshot=screenshot)
