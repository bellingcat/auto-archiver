
from telethon.sync import TelegramClient
from telethon.errors import ChannelInvalidError
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors.rpcerrorlist import UserAlreadyParticipantError, FloodWaitError, InviteRequestSentError, InviteHashExpiredError
from loguru import logger
from tqdm import tqdm
import re, time, json, os

from . import Archiver
from ..core import Metadata, Media, ArchivingContext


class TelethonArchiver(Archiver):
    name = "telethon_archiver"
    link_pattern = re.compile(r"https:\/\/t\.me(\/c){0,1}\/(.+)\/(\d+)")
    invite_pattern = re.compile(r"t.me(\/joinchat){0,1}\/\+?(.+)")

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.assert_valid_string("api_id")
        self.assert_valid_string("api_hash")

        self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)

    @staticmethod
    def configs() -> dict:
        return {
            "api_id": {"default": None, "help": "telegram API_ID value, go to https://my.telegram.org/apps"},
            "api_hash": {"default": None, "help": "telegram API_HASH value, go to https://my.telegram.org/apps"},
            "bot_token": {"default": None, "help": "optional, but allows access to more content such as large videos, talk to @botfather"},
            "session_file": {"default": "secrets/anon", "help": "optional, records the telegram login session for future usage, '.session' will be appended to the provided value."},
            "join_channels": {"default": True, "help": "disables the initial setup with channel_invites config, useful if you have a lot and get stuck"},
            "channel_invites": {
                "default": {},
                "help": "(JSON string) private channel invite links (format: t.me/joinchat/HASH OR t.me/+HASH) and (optional but important to avoid hanging for minutes on startup) channel id (format: CHANNEL_ID taken from a post url like https://t.me/c/CHANNEL_ID/1), the telegram account will join any new channels on setup",
                "cli_set": lambda cli_val, cur_val: dict(cur_val, **json.loads(cli_val))
            }
        }

    def is_rearchivable(self, url: str) -> bool:
        # telegram posts are static
        return False

    def setup(self) -> None:
        """
        1. trigger login process for telegram or proceed if already saved in a session file
        2. joins channel_invites where needed
        """
        logger.info(f"SETUP {self.name} checking login...")
        with self.client.start():
            logger.success(f"SETUP {self.name} login works.")

        if self.join_channels and len(self.channel_invites):
            logger.info(f"SETUP {self.name} joining channels...")
            with self.client.start():
                # get currently joined channels
                # https://docs.telethon.dev/en/stable/modules/custom.html#module-telethon.tl.custom.dialog
                joined_channel_ids = [c.id for c in self.client.get_dialogs() if c.is_channel]
                logger.info(f"already part of {len(joined_channel_ids)} channels")

                i = 0
                pbar = tqdm(desc=f"joining {len(self.channel_invites)} invite links", total=len(self.channel_invites))
                while i < len(self.channel_invites):
                    channel_invite = self.channel_invites[i]
                    channel_id = channel_invite.get("id", False)
                    invite = channel_invite["invite"]
                    if (match := self.invite_pattern.search(invite)):
                        try:
                            if channel_id:
                                ent = self.client.get_entity(int(channel_id))  # fails if not a member
                            else:
                                ent = self.client.get_entity(invite)  # fails if not a member
                                logger.warning(f"please add the property id='{ent.id}' to the 'channel_invites' configuration where {invite=}, not doing so can lead to a minutes-long setup time due to telegram's rate limiting.")
                        except ValueError as e:
                            logger.info(f"joining new channel {invite=}")
                            try:
                                self.client(ImportChatInviteRequest(match.group(2)))
                            except UserAlreadyParticipantError as e:
                                logger.info(f"already joined {invite=}")
                            except InviteRequestSentError:
                                logger.warning(f"already sent a join request with {invite} still no answer")
                            except InviteHashExpiredError:
                                logger.warning(f"{invite=} has expired please find a more recent one")
                            except Exception as e:
                                logger.error(f"could not join channel with {invite=} due to {e}")
                        except FloodWaitError as e:
                            logger.warning(f"got a flood error, need to wait {e.seconds} seconds")
                            time.sleep(e.seconds)
                            continue
                    else:
                        logger.warning(f"Invalid invite link {invite}")
                    i += 1
                    pbar.update()

    def download(self, item: Metadata) -> Metadata:
        """
        if this url is archivable will download post info and look for other posts from the same group with media.
        can handle private/public channels
        """
        url = item.get_url()
        # detect URLs that we definitely cannot handle
        match = self.link_pattern.search(url)
        logger.debug(f"TELETHON: {match=}")
        if not match: return False

        is_private = match.group(1) == "/c"
        chat = int(match.group(2)) if is_private else match.group(2)
        post_id = int(match.group(3))

        result = Metadata()

        # NB: not using bot_token since then private channels cannot be archived: self.client.start(bot_token=self.bot_token)
        with self.client.start():
        # with self.client.start(bot_token=self.bot_token):
            try:
                post = self.client.get_messages(chat, ids=post_id)
            except ValueError as e:
                logger.error(f"Could not fetch telegram {url} possibly it's private: {e}")
                return False
            except ChannelInvalidError as e:
                logger.error(f"Could not fetch telegram {url}. This error may be fixed if you setup a bot_token in addition to api_id and api_hash (but then private channels will not be archived, we need to update this logic to handle both): {e}")
                return False

            logger.debug(f"TELETHON GOT POST {post=}")
            if post is None: return False

            media_posts = self._get_media_posts_in_group(chat, post)
            logger.debug(f'got {len(media_posts)=} for {url=}')

            tmp_dir = ArchivingContext.get_tmp_dir()

            group_id = post.grouped_id if post.grouped_id is not None else post.id
            title = post.message
            for mp in media_posts:
                if len(mp.message) > len(title): title = mp.message  # save the longest text found (usually only 1)

                # media can also be in entities
                if mp.entities:
                    other_media_urls = [e.url for e in mp.entities if hasattr(e, "url") and e.url and self._guess_file_type(e.url) in ["video", "image", "audio"]]
                    if len(other_media_urls):
                        logger.debug(f"Got {len(other_media_urls)} other media urls from {mp.id=}: {other_media_urls}")
                    for i, om_url in enumerate(other_media_urls):
                        filename = self.download_from_url(om_url, f'{chat}_{group_id}_{i}', item)
                        result.add_media(Media(filename=filename), id=f"{group_id}_{i}")

                filename_dest = os.path.join(tmp_dir, f'{chat}_{group_id}', str(mp.id))
                filename = self.client.download_media(mp.media, filename_dest)
                if not filename:
                    logger.debug(f"Empty media found, skipping {str(mp)=}")
                    continue
                result.add_media(Media(filename))

            result.set_content(str(post)).set_title(title).set_timestamp(post.date)
        return result.success("telethon")

    def _get_media_posts_in_group(self, chat, original_post, max_amp=10):
        """
        Searches for Telegram posts that are part of the same group of uploads
        The search is conducted around the id of the original post with an amplitude
        of `max_amp` both ways
        Returns a list of [post] where each post has media and is in the same grouped_id
        """
        if getattr(original_post, "grouped_id", None) is None:
            return [original_post] if getattr(original_post, "media", False) else []

        search_ids = [i for i in range(original_post.id - max_amp, original_post.id + max_amp + 1)]
        posts = self.client.get_messages(chat, ids=search_ids)
        media = []
        for post in posts:
            if post is not None and post.grouped_id == original_post.grouped_id and post.media is not None:
                media.append(post)
        return media
