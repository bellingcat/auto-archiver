import json, os, traceback, uuid
import tiktok_downloader
from loguru import logger

from . import Archiver
from ..core import Metadata, Media, ArchivingContext


class TiktokArchiver(Archiver):
    name = "tiktok_archiver"

    def __init__(self, config: dict) -> None:
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {}

    def is_rearchivable(self, url: str) -> bool:
        # TikTok posts are static
        return False

    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()
        if 'tiktok.com' not in url:
            return False

        result = Metadata()
        try:
            info = tiktok_downloader.info_post(url)
            result.set_title(info.desc)
            result.set_timestamp(info.create_time)
            result.set_content(json.dumps({
                "cover": info.cover,
                "author": info.author,
                "music_title": info.author,
                "caption": getattr(info, "caption", info.desc),
            }, ensure_ascii=False, indent=4))
        except:
            error = traceback.format_exc()
            logger.warning(f'Other Tiktok error {error}')

        try:
            filename = os.path.join(ArchivingContext.get_tmp_dir(), f'{str(uuid.uuid4())[0:8]}.mp4')
            tiktok_media = tiktok_downloader.snaptik(url).get_media()

            if len(tiktok_media) <= 0:
                logger.debug(f"TikTok: could not get media from {url=}")
                return False

            logger.info(f'downloading video {filename=}')
            tiktok_media[0].download(filename)

            result.add_media(Media(filename))
            return result.success("tiktok")
        except:
            error = traceback.format_exc()
            logger.warning(f'Other Tiktok error {error}')
