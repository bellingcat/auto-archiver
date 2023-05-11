
from telethon.sync import TelegramClient
from loguru import logger
import time, os
from sqlite3 import OperationalError
from . import Archiver
from ..core import Metadata, Media, ArchivingContext


class InstagramTbotArchiver(Archiver):
    """
    calls a telegram bot to fetch instagram posts/stories... and gets available media from it
    https://github.com/adw0rd/instagrapi
    https://t.me/instagram_load_bot
    """
    name = "instagram_tbot_archiver"

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.assert_valid_string("api_id")
        self.assert_valid_string("api_hash")
        self.timeout = int(self.timeout)
        try:
            self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
        except OperationalError as e:
            logger.error(f"Unable to access the {self.session_file} session, please make sure you don't use the same session file here and in telethon_archiver. if you do then disable at least one of the archivers for the 1st time you setup telethon session: {e}")

    @staticmethod
    def configs() -> dict:
        return {
            "api_id": {"default": None, "help": "telegram API_ID value, go to https://my.telegram.org/apps"},
            "api_hash": {"default": None, "help": "telegram API_HASH value, go to https://my.telegram.org/apps"},
            "session_file": {"default": "secrets/anon-insta", "help": "optional, records the telegram login session for future usage, '.session' will be appended to the provided value."},
            "timeout": {"default": 45, "help": "timeout to fetch the instagram content in seconds."},
        }

    def setup(self) -> None:
        logger.info(f"SETUP {self.name} checking login...")
        with self.client.start():
            logger.success(f"SETUP {self.name} login works.")

    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()
        if not "instagram.com" in url: return False

        result = Metadata()
        tmp_dir = ArchivingContext.get_tmp_dir()
        with self.client.start():
            chat = self.client.get_entity("instagram_load_bot")
            since_id = self.client.send_message(entity=chat, message=url).id

            attempts = 0
            seen_media = []
            message = ""
            time.sleep(3)
            # media is added before text by the bot so it can be used as a stop-logic mechanism
            while attempts < (self.timeout - 3) and (not message or not len(seen_media)):
                attempts += 1
                time.sleep(1)
                for post in self.client.iter_messages(chat, min_id=since_id):
                    since_id = max(since_id, post.id)
                    if post.media and post.id not in seen_media:
                        filename_dest = os.path.join(tmp_dir, f'{chat.id}_{post.id}')
                        media = self.client.download_media(post.media, filename_dest)
                        if media: 
                            result.add_media(Media(media))
                            seen_media.append(post.id)
                    if post.message: message += post.message

            if "You must enter a URL to a post" in message: 
                logger.debug(f"invalid link {url=} for {self.name}: {message}")
                return False
                
            if message:
                result.set_content(message).set_title(message[:128])

            return result.success("insta-via-bot")
