import os
import requests
from bs4 import BeautifulSoup
from loguru import logger
import re
import html
from dataclasses import dataclass

from storages import Storage
from .base_archiver import Archiver, ArchiveResult
from telethon.sync import TelegramClient


@dataclass
class TelegramConfig:
    api_id: str
    api_hash: str


class TelethonArchiver(Archiver):
    name = "telethon"
    link_pattern = re.compile(r"https:\/\/t\.me(\/c){0,1}\/(.+)\/(.+)")

    def __init__(self, storage: Storage, driver, config: TelegramConfig):
        super().__init__(storage, driver)
        self.client = TelegramClient("./anon", config.api_id, config.api_hash)

    def download(self, url, check_if_exists=False):
        # detect URLs that we definitely cannot handle
        matches = self.link_pattern.findall(url)
        if not len(matches):
            return False

        status = "success"
        screenshot = self.get_screenshot(url)

        with self.client.start():
            matches = list(matches[0])
            chat, post_id = matches[-2], matches[-1]
            
            post_id = int(post_id)
            post = self.client.get_messages(chat, ids=post_id)

            if post.media is not None:
                key = f'{chat}_{post_id}'
                filename = 'tmp/' + key

                filename = self.client.download_media(post.media, filename)
                key += os.path.splitext(filename)[1]  # add the extension to the key

                cdn_url = self.storage.get_cdn_url(key)
                hash = self.get_hash(filename)
                if check_if_exists and self.storage.exists(key):
                    status = 'already archived'
                else:
                    self.storage.upload(filename, key)

                key_thumb, thumb_index = self.get_thumbnails(filename, key)
                os.remove(filename)
                return ArchiveResult(status=status, cdn_url=cdn_url, thumbnail=key_thumb, thumbnail_index=thumb_index, title=post.message, timestamp=post.date, hash=hash, screenshot=screenshot)
            else:
                return ArchiveResult(status="success", cdn_url=cdn_url, title=post.message, timestamp=post.date, hash=hash, screenshot=screenshot)

    def get_post_channel_and_id_from_url(self, url):
        parts = url.split('t.me/')[1]
        if parts.startswith('s/'):
            parts = parts.split('s/')[1]
        channel_info = parts.split('/')
        return channel_info[0], channel_info[1]
