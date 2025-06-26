import os
import shutil
import re
import time
from pathlib import Path
from datetime import date

from telethon import functions
from telethon.sync import TelegramClient
from telethon.errors import ChannelInvalidError
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors.rpcerrorlist import (
    UserAlreadyParticipantError,
    FloodWaitError,
    InviteRequestSentError,
    InviteHashExpiredError,
)

from tqdm import tqdm
from auto_archiver.utils.custom_logger import logger

from auto_archiver.core import Extractor
from auto_archiver.core import Metadata, Media
from auto_archiver.utils import random_str


class TelethonExtractor(Extractor):
    valid_url = re.compile(r"https:\/\/t\.me(\/c){0,1}\/(.+?)(\/s){0,1}\/(\d+)")
    invite_pattern = re.compile(r"t.me(\/joinchat){0,1}\/\+?(.+)")

    def setup(self) -> None:
        """
        1. makes a copy of session_file that is removed in cleanup
        2. trigger login process for telegram or proceed if already saved in a session file
        3. joins channel_invites where needed
        """
        logger.info(f"SETUP {self.name} checking login...")

        # in case the user already added '.session' to the session_file
        base_session_name = self.session_file.removesuffix(".session")
        base_session_filepath = f"{base_session_name}.session"

        if self.session_file and not os.path.exists(base_session_filepath):
            logger.warning(
                f"SETUP - Session file {base_session_filepath} does not exist for {self.name}, creating an empty one."
            )
            Path(base_session_filepath).touch()

        # make a copy of the session that is used exclusively with this archiver instance
        self.session_file = os.path.join(
            os.path.dirname(base_session_filepath), f"telethon-{date.today().strftime('%Y-%m-%d')}{random_str(8)}"
        )
        logger.debug(f"Making a copy of the session file {base_session_filepath} to {self.session_file}.session")
        shutil.copy(base_session_filepath, f"{self.session_file}.session")

        # initiate the client
        self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)

        with self.client.start():
            logger.info(f"SETUP {self.name} login works.")

        if self.join_channels and len(self.channel_invites):
            logger.info(f"SETUP {self.name} joining channels...")
            with self.client.start():
                # get currently joined channels
                # https://docs.telethon.dev/en/stable/modules/custom.html#module-telethon.tl.custom.dialog
                joined_channel_ids = [c.id for c in self.client.get_dialogs() if c.is_channel]
                logger.info(f"Already part of {len(joined_channel_ids)} channels")

                i = 0
                pbar = tqdm(desc=f"joining {len(self.channel_invites)} invite links", total=len(self.channel_invites))
                while i < len(self.channel_invites):
                    channel_invite = self.channel_invites[i]
                    channel_id = channel_invite.get("id", False)
                    invite = channel_invite["invite"]
                    if match := self.invite_pattern.search(invite):
                        try:
                            if channel_id:
                                ent = self.client.get_entity(int(channel_id))  # fails if not a member
                            else:
                                ent = self.client.get_entity(invite)  # fails if not a member
                                logger.warning(
                                    f"Please add the property id='{ent.id}' to the 'channel_invites' configuration where {invite=}, not doing so can lead to a minutes-long setup time due to telegram's rate limiting."
                                )
                        except ValueError:
                            logger.info(f"Joining new channel {invite=}")
                            try:
                                self.client(ImportChatInviteRequest(match.group(2)))
                            except UserAlreadyParticipantError:
                                logger.info(f"Already joined {invite=}")
                            except InviteRequestSentError:
                                logger.warning(f"Already sent a join request with {invite} still no answer")
                            except InviteHashExpiredError:
                                logger.warning(f"{invite=} has expired please find a more recent one")
                            except Exception as e:
                                logger.error(f"Could not join channel with {invite=} due to {e}")
                        except FloodWaitError as e:
                            logger.warning(f"Got a flood error, need to wait {e.seconds} seconds")
                            time.sleep(e.seconds)
                            continue
                    else:
                        logger.warning(f"Invalid invite link {invite}")
                    i += 1
                    pbar.update()

    def cleanup(self) -> None:
        logger.info(f"CLEANUP {self.name} - removing session file {self.session_file}.session")
        session_file_name = f"{self.session_file}.session"
        if os.path.exists(session_file_name):
            os.remove(session_file_name)

    def download(self, item: Metadata) -> Metadata:
        """
        if this url is archivable will download post info and look for other posts from the same group with media.
        can handle private/public channels
        """
        url = item.get_url()
        # detect URLs that we definitely cannot handle
        match = self.valid_url.search(url)
        logger.debug(f"Found telethon url {match=}")
        if not match:
            return False

        is_private = match.group(1) == "/c"
        chat = int(match.group(2)) if is_private else match.group(2)
        is_story = match.group(3) == "/s"
        post_id = int(match.group(4))

        result = Metadata()

        # NB: not using bot_token since then private channels cannot be archived: self.client.start(bot_token=self.bot_token)
        with self.client.start():
            # with self.client.start(bot_token=self.bot_token):
            if is_story:
                try:
                    stories = self.client(functions.stories.GetStoriesByIDRequest(peer=chat, id=[post_id]))
                    if not stories.stories:
                        logger.info("No stories found, possibly it's private or the story has expired.")
                        return False
                    story = stories.stories[0]
                    logger.debug(f"Got story {story.id=} {story.date=} {story.expire_date=}")
                    result.set_timestamp(story.date).set("views", story.views.to_dict()).set(
                        "expire_date", story.expire_date
                    )

                    # download the story media
                    filename_dest = os.path.join(self.tmp_dir, f"{chat}_{post_id}", str(story.id))
                    if filename := self.client.download_media(story.media, filename_dest):
                        result.add_media(Media(filename))
                except Exception as e:
                    logger.error(f"Error fetching story {post_id} from {chat}: {e}")
                    return False
            else:
                try:
                    post = self.client.get_messages(chat, ids=post_id)
                except ValueError as e:
                    logger.error(f"Could not fetch telegram URL possibly it's private: {e}")
                    return False
                except ChannelInvalidError as e:
                    logger.error(
                        f"Could not fetch telegram URL. This error may be fixed if you setup a bot_token in addition to api_id and api_hash (but then private channels will not be archived, we need to update this logic to handle both): {e}"
                    )
                    return False

                logger.debug(f"Got post {post=}")
                if post is None:
                    return False

                media_posts = self._get_media_posts_in_group(chat, post)
                logger.debug(f"Got {len(media_posts)=}")

                group_id = post.grouped_id if post.grouped_id is not None else post.id
                title = post.message
                for mp in media_posts:
                    if len(mp.message) > len(title):
                        title = mp.message  # save the longest text found (usually only 1)

                    # media can also be in entities
                    if mp.entities:
                        other_media_urls = [
                            e.url
                            for e in mp.entities
                            if hasattr(e, "url")
                            and e.url
                            and self._guess_file_type(e.url) in ["video", "image", "audio"]
                        ]
                        if len(other_media_urls):
                            logger.debug(
                                f"Got {len(other_media_urls)} other media urls from {mp.id=}: {other_media_urls}"
                            )
                        for i, om_url in enumerate(other_media_urls):
                            filename = self.download_from_url(om_url, f"{chat}_{group_id}_{i}")
                            result.add_media(Media(filename=filename), id=f"{group_id}_{i}")

                    filename_dest = os.path.join(self.tmp_dir, f"{chat}_{group_id}", str(mp.id))
                    filename = self.client.download_media(mp.media, filename_dest)
                    if not filename:
                        logger.debug(f"Empty media found, skipping {str(mp)=}")
                        continue
                    result.add_media(Media(filename))

                result.set_title(title).set_timestamp(post.date).set("api_data", post.to_dict())
                if post.message != title:
                    result.set_content(post.message)
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

        search_ids = list(range(original_post.id - max_amp, original_post.id + max_amp + 1))
        posts = self.client.get_messages(chat, ids=search_ids)
        media = []
        for post in posts:
            if post is not None and post.grouped_id == original_post.grouped_id and post.media is not None:
                media.append(post)
        return media
