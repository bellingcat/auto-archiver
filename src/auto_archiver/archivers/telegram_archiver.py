import requests, re, html
from bs4 import BeautifulSoup
from loguru import logger

from . import Archiver
from ..core import Metadata, Media


class TelegramArchiver(Archiver):
    """
    Archiver for telegram that does not require login, but the telethon_archiver is much more advised, will only return if at least one image or one video is found
    """
    name = "telegram_archiver"

    def __init__(self, config: dict) -> None:
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {}

    def is_rearchivable(self, url: str) -> bool:
        # telegram posts are static
        return False

    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()
        # detect URLs that we definitely cannot handle
        if 't.me' != item.netloc:
            return False

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
        }

        # TODO: check if we can do this more resilient to variable URLs
        if url[-8:] != "?embed=1":
            url += "?embed=1"

        t = requests.get(url, headers=headers)
        s = BeautifulSoup(t.content, 'html.parser')

        result = Metadata()
        result.set_content(html.escape(str(t.content)))
        if (timestamp := (s.find_all('time') or [{}])[0].get('datetime')):
            result.set_timestamp(timestamp)

        video = s.find("video")
        if video is None:
            logger.warning("could not find video")
            image_tags = s.find_all(class_="js-message_photo")

            image_urls = []
            for im in image_tags:
                urls = [u.replace("'", "") for u in re.findall(r'url\((.*?)\)', im['style'])]
                image_urls += urls

            if not len(image_urls): return False
            for img_url in image_urls:
                result.add_media(Media(self.download_from_url(img_url)))
        else:
            video_url = video.get('src')
            m_video = Media(self.download_from_url(video_url))
            # extract duration from HTML
            try:
                duration = s.find_all('time')[0].contents[0]
                if ':' in duration:
                    duration = float(duration.split(
                        ':')[0]) * 60 + float(duration.split(':')[1])
                else:
                    duration = float(duration)
                m_video.set("duration", duration)
            except: pass
            result.add_media(m_video)

        return result.success("telegram")
