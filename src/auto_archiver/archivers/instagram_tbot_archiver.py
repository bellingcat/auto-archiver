
from telethon.sync import TelegramClient
from loguru import logger
import time, os

from . import Archiver
from ..core import Metadata, Media


class InstagramTbotArchiver(Archiver):
    """
    calls a telegram bot to fetch instagram posts/stories...
    https://github.com/adw0rd/instagrapi
    https://t.me/instagram_load_bot
    """
    name = "instagram_tbot_archiver"

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.assert_valid_string("api_id")
        self.assert_valid_string("api_hash")
        self.timeout = int(self.timeout)
        self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)

    @staticmethod
    def configs() -> dict:
        return {
            "api_id": {"default": None, "help": "telegram API_ID value, go to https://my.telegram.org/apps"},
            "api_hash": {"default": None, "help": "telegram API_HASH value, go to https://my.telegram.org/apps"},
            "session_file": {"default": "secrets/anon", "help": "optional, records the telegram login session for future usage, '.session' will be appended to the provided value."},
            "timeout": {"default": 15, "help": "timeout to fetch the instagram content in seconds."},
        }

    def setup(self) -> None:
        logger.info(f"SETUP {self.name} checking login...")
        with self.client.start():
            logger.success(f"SETUP {self.name} login works.")

    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()
        if not "instagram.com" in url: return False

        result = Metadata()
        tmp_dir = item.get_tmp_dir()
        with self.client.start():
            chat = self.client.get_entity("instagram_load_bot")
            since_id = self.client.send_message(entity=chat, message=url).id

            attempts = 0
            media = None
            message = ""
            time.sleep(4)
            while attempts < self.timeout and (not message or not media):
                attempts += 1
                time.sleep(1)
                for post in self.client.iter_messages(chat, min_id=since_id):
                    since_id = max(since_id, post.id)
                    if post.media and not media:
                        filename_dest = os.path.join(tmp_dir, f'{chat.id}_{post.id}')
                        media = self.client.download_media(post.media, filename_dest)
                        if media: result.add_media(Media(media))
                    if post.message: message += post.message

            if message:
                result.set_content(message).set_title(message[:128])

            return result.success("insta-via-bot")
