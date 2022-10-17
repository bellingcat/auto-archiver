import os, re

import html
from loguru import logger
from telethon.sync import TelegramClient
from telethon.errors import ChannelInvalidError

from storages import Storage
from .base_archiver import Archiver, ArchiveResult
from configs import Config
from utils import getattr_or


class TelethonArchiver(Archiver):
    name = "telethon"
    link_pattern = re.compile(r"https:\/\/t\.me(\/c){0,1}\/(.+)\/(\d+)")

    def __init__(self, storage: Storage, config: Config):
        super().__init__(storage, config)
        if config.telegram_config:
            c = config.telegram_config
            self.client = TelegramClient("./anon", c.api_id, c.api_hash)
            self.bot_token = c.bot_token

    def _get_media_posts_in_group(self, chat, original_post, max_amp=10):
        """
        Searches for Telegram posts that are part of the same group of uploads
        The search is conducted around the id of the original post with an amplitude
        of `max_amp` both ways
        Returns a list of [post] where each post has media and is in the same grouped_id
        """
        if getattr_or(original_post, "grouped_id") is None:
            return [original_post] if getattr_or(original_post, "media") else []

        search_ids = [i for i in range(original_post.id - max_amp, original_post.id + max_amp + 1)]
        posts = self.client.get_messages(chat, ids=search_ids)
        media = []
        for post in posts:
            if post is not None and post.grouped_id == original_post.grouped_id and post.media is not None:
                media.append(post)
        return media

    def download(self, url, check_if_exists=False):
        if not hasattr(self, "client"):
            logger.warning('Missing Telethon config')
            return False

        # detect URLs that we definitely cannot handle
        matches = self.link_pattern.findall(url)
        if not len(matches):
            return False

        status = "success"

        # app will ask (stall for user input!) for phone number and auth code if anon.session not found
        with self.client.start(bot_token=self.bot_token):
            matches = list(matches[0])
            chat, post_id = matches[1], matches[2]

            post_id = int(post_id)

            try:
                post = self.client.get_messages(chat, ids=post_id)
            except ValueError as e:
                logger.error(f"Could not fetch telegram {url} possibly it's private: {e}")
                return False
            except ChannelInvalidError as e:
                logger.error(f"Could not fetch telegram {url}. This error can be fixed if you setup a bot_token in addition to api_id and api_hash: {e}")
                return False

            if post is None: return False

            media_posts = self._get_media_posts_in_group(chat, post)
            logger.debug(f'got {len(media_posts)=} for {url=}')

            screenshot = self.get_screenshot(url)
            wacz = self.get_wacz(url)

            if len(media_posts) > 0:
                key = self.get_html_key(url)

                if check_if_exists and self.storage.exists(key):
                    # only s3 storage supports storage.exists as not implemented on gd
                    cdn_url = self.storage.get_cdn_url(key)
                    return ArchiveResult(status='already archived', cdn_url=cdn_url, title=post.message, timestamp=post.date, screenshot=screenshot, wacz=wacz)

                key_thumb, thumb_index = None, None
                group_id = post.grouped_id if post.grouped_id is not None else post.id
                uploaded_media = []
                message = post.message
                for mp in media_posts:
                    if len(mp.message) > len(message): message = mp.message

                    # media can also be in entities
                    if mp.entities:
                        other_media_urls = [e.url for e in mp.entities if hasattr(e, "url") and e.url and self._guess_file_type(e.url) in ["video", "image"]]
                        logger.debug(f"Got {len(other_media_urls)} other medial urls from {mp.id=}: {other_media_urls}")
                        for om_url in other_media_urls:
                            filename = os.path.join(Storage.TMP_FOLDER, f'{chat}_{group_id}_{self._get_key_from_url(om_url)}')
                            self.download_from_url(om_url, filename)
                            key = filename.split(Storage.TMP_FOLDER)[1]
                            self.storage.upload(filename, key)
                            hash = self.get_hash(filename)
                            cdn_url = self.storage.get_cdn_url(key)
                            uploaded_media.append({'cdn_url': cdn_url, 'key': key, 'hash': hash})

                    filename_dest = os.path.join(Storage.TMP_FOLDER, f'{chat}_{group_id}', str(mp.id))
                    filename = self.client.download_media(mp.media, filename_dest)
                    if not filename:
                        logger.debug(f"Empty media found, skipping {str(mp)=}")
                        continue

                    key = filename.split(Storage.TMP_FOLDER)[1]
                    self.storage.upload(filename, key)
                    hash = self.get_hash(filename)
                    cdn_url = self.storage.get_cdn_url(key)
                    uploaded_media.append({'cdn_url': cdn_url, 'key': key, 'hash': hash})
                    if key_thumb is None:
                        key_thumb, thumb_index = self.get_thumbnails(filename, key)
                    os.remove(filename)

                page_cdn, page_hash, _ = self.generate_media_page_html(url, uploaded_media, html.escape(str(post)))

                return ArchiveResult(status=status, cdn_url=page_cdn, title=message, timestamp=post.date, hash=page_hash, screenshot=screenshot, thumbnail=key_thumb, thumbnail_index=thumb_index, wacz=wacz)

            page_cdn, page_hash, _ = self.generate_media_page_html(url, [], html.escape(str(post)))
            return ArchiveResult(status=status, cdn_url=page_cdn, title=post.message, timestamp=getattr_or(post, "date"), hash=page_hash, screenshot=screenshot, wacz=wacz)
