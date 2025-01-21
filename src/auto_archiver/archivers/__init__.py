"""
Archivers are responsible for retrieving the content from various external platforms.
They act as specialized modules, each tailored to interact with a specific platform,
service, or data source. The archivers collectively enable the tool to comprehensively
collect and preserve a variety of content types, such as posts, images, videos and metadata.

"""
from .archiver import Archiver
from .telethon_archiver import TelethonArchiver
from .twitter_archiver import TwitterArchiver
from .twitter_api_archiver import TwitterApiArchiver
from .instagram_archiver import InstagramArchiver
from .instagram_tbot_archiver import InstagramTbotArchiver
from .tiktok_archiver import TiktokArchiver
from .telegram_archiver import TelegramArchiver
from .vk_archiver import VkArchiver
from .youtubedl_archiver import YoutubeDLArchiver
from .instagram_api_archiver import InstagramAPIArchiver
from .bluesky_archiver import BlueskyArchiver
