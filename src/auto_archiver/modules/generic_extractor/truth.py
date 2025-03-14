from typing import Type

from auto_archiver.utils import traverse_obj
from auto_archiver.core.metadata import Metadata, Media
from auto_archiver.core.extractor import Extractor
from yt_dlp.extractor.common import InfoExtractor

from dateutil.parser import parse as parse_dt

from .dropin import GenericDropin


class Truth(GenericDropin):
    def extract_post(self, url, ie_instance: InfoExtractor) -> dict:
        video_id = ie_instance._match_id(url)
        truthsocial_url = f"https://truthsocial.com/api/v1/statuses/{video_id}"
        return ie_instance._download_json(truthsocial_url, video_id)

    def skip_ytdlp_download(self, url, ie_instance: Type[InfoExtractor]) -> bool:
        return True

    def create_metadata(self, post: dict, ie_instance: InfoExtractor, archiver: Extractor, url: str) -> Metadata:
        """
        Creates metadata from a truth social post

        Only used for posts that contain no media. ytdlp.TruthIE extractor can handle posts with media

        Format is:

        {'id': '109598702184774628', 'created_at': '2022-12-29T19:51:18.161Z', 'in_reply_to_id': None, 'quote_id': None, 'in_reply_to_account_id': None, 'sensitive': False, 'spoiler_text': '', 'visibility': 'public', 'language': 'en', 'uri': 'https://truthsocial.com/@bbcnewa/109598702184774628', 'url': 'https://truthsocial.com/@bbcnewa/109598702184774628', 'content': '<p>Pele, regarded by many as football\'s greatest ever player, has died in Brazil at the age of 82. <a href="https://www.bbc.com/sport/football/42751517" rel="nofollow noopener noreferrer" target="_blank"><span class="invisible">https://www.</span><span class="ellipsis">bbc.com/sport/football/4275151</span><span class="invisible">7</span></a></p>', 'account': {'id': '107905163010312793', 'username': 'bbcnewa', 'acct': 'bbcnewa', 'display_name': 'BBC News', 'locked': False, 'bot': False, 'discoverable': True, 'group': False, 'created_at': '2022-03-05T17:42:01.159Z', 'note': '<p>News, features and analysis by the BBC</p>', 'url': 'https://truthsocial.com/@bbcnewa', 'avatar': 'https://static-assets-1.truthsocial.com/tmtg:prime-ts-assets/accounts/avatars/107/905/163/010/312/793/original/e7c07550dc22c23a.jpeg', 'avatar_static': 'https://static-assets-1.truthsocial.com/tmtg:prime-ts-assets/accounts/avatars/107/905/163/010/312/793/original/e7c07550dc22c23a.jpeg', 'header': 'https://static-assets-1.truthsocial.com/tmtg:prime-ts-assets/accounts/headers/107/905/163/010/312/793/original/a00eeec2b57206c7.jpeg', 'header_static': 'https://static-assets-1.truthsocial.com/tmtg:prime-ts-assets/accounts/headers/107/905/163/010/312/793/original/a00eeec2b57206c7.jpeg', 'followers_count': 1131, 'following_count': 3, 'statuses_count': 9, 'last_status_at': '2024-11-12', 'verified': False, 'location': '', 'website': 'https://www.bbc.com/news', 'unauth_visibility': True, 'chats_onboarded': True, 'feeds_onboarded': True, 'accepting_messages': False, 'show_nonmember_group_statuses': None, 'emojis': [], 'fields': [], 'tv_onboarded': True, 'tv_account': False}, 'media_attachments': [], 'mentions': [], 'tags': [], 'card': None, 'group': None, 'quote': None, 'in_reply_to': None, 'reblog': None, 'sponsored': False, 'replies_count': 1, 'reblogs_count': 0, 'favourites_count': 2, 'favourited': False, 'reblogged': False, 'muted': False, 'pinned': False, 'bookmarked': False, 'poll': None, 'emojis': []}
        """

        result = Metadata()
        result.set_url(url)
        timestamp = post["created_at"]  # format is 2022-12-29T19:51:18.161Z
        result.set_timestamp(parse_dt(timestamp))
        result.set("description", post["content"])
        result.set("author", post["account"]["username"])

        for key in [
            "replies_count",
            "reblogs_count",
            "favourites_count",
            ("account", "followers_count"),
            ("account", "following_count"),
            ("account", "statuses_count"),
            ("account", "display_name"),
            "language",
            "in_reply_to_account",
            "replies_count",
        ]:
            if isinstance(key, tuple):
                store_key = " ".join(key)
            else:
                store_key = key
            result.set(store_key, traverse_obj(post, key))

        # add the media
        for media in post.get("media_attachments", []):
            filename = archiver.download_from_url(media["url"])
            result.add_media(Media(filename), id=media.get("id"))

        return result
