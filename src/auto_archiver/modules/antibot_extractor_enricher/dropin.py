import os
from loguru import logger
from seleniumbase import SB
import yt_dlp

from auto_archiver.core import Extractor, Media, Metadata
from auto_archiver.utils.misc import ydl_entry_to_filename


class Dropin:
    """
    A class to handle drop-in functionality for the antibot extractor enricher module.
    This class is designed to be a base class for drop-ins that can handle specific websites.
    """

    def __init__(self, sb: SB, extractor: Extractor):
        """
        Initialize the Dropin with the given SeleniumBase instance.

        :param sb: An instance of the SeleniumBase class that this drop-in will use.
        :param extractor: An instance of the Extractor class that this drop-in will use.
        """
        self.sb: SB = sb
        self.extractor: Extractor = extractor

    @staticmethod
    def suitable(url: str) -> bool:
        """
        Check if the URL is suitable for processing with this dropin.
        :param url: The URL to check.
        :return: True if the URL is suitable for processing, False otherwise.
        """
        raise NotImplementedError("This method should be implemented in the subclass")

    @staticmethod
    def sanitize_url(url: str) -> str:
        """
        Used to clean URLs before processing them.
        """
        return url

    @staticmethod
    def images_selectors() -> str:
        """
        CSS selector to find images in the HTML page
        """
        return "img"

    @staticmethod
    def video_selectors() -> str:
        """
        CSS selector to find videos in the HTML page.
        """
        return "video, source"

    def js_for_image_css_selectors(self) -> str:
        """
        A configurable JS script that receives a css selector from the dropin itself and returns an array of Image elements according to the selection.

        You can overwrite this instead of `images_selector` for more control over scraped images.
        """
        return f"""
            return Array.from(document.querySelectorAll("{self.images_selectors()}")).map(el => el.src || el.href).filter(Boolean);
        """

    def js_for_video_css_selectors(self) -> str:
        """
        A configurable JS script that receives a css selector from the dropin itself and returns an array of Video elements according to the selection.

        You can overwrite this instead of `video_selector` for more control over scraped videos.
        """
        return f"""
            return Array.from(document.querySelectorAll("{self.video_selectors()}")).map(el => el.src || el.href).filter(Boolean);
        """

    def open_page(self, url) -> bool:
        """
        Make sure the page is opened, even if it requires authentication, captcha solving, etc.
        :param url: The URL to open.
        :return: True if success, False otherwise.
        """
        raise NotImplementedError("This method should be implemented in the subclass")

    def add_extra_media(self, to_enrich: Metadata) -> tuple[int, int]:
        """
        Extract image and/or video data from the currently open post with SeleniumBase. Media is added to the `to_enrich` Metadata object.
        :return: A tuple (number of Images added, number of Videos added).
        """
        return 0, 0

    def _get_username_password(self, site) -> tuple[str, str]:
        """
        Get the username and password for the site from the extractor's auth data.
        :return: A tuple (username, password).
        """
        auth = self.extractor.auth_for_site(site)
        username = auth.get("username", "")
        password = auth.get("password", "")
        if not username or not password:
            raise ValueError(f"{site} authentication requires a username and password.")
        return username, password

    def _download_videos_with_ytdlp(self, video_urls: list[str], to_enrich: Metadata) -> int:
        """
        Download videos using yt-dlp.
        :param video_urls: List of video URLs to download.
        :return: The number of videos downloaded.
        """
        if type(self.extractor.max_download_videos) is int:
            video_urls = video_urls[: self.extractor.max_download_videos]

        if not video_urls:
            return 0

        ydl_options = [
            "-o",
            os.path.join(self.extractor.tmp_dir, "%(id)s.%(ext)s"),
            "--quiet",
            "--no-playlist",
            "--no-write-subs",
            "--no-write-auto-subs",
            "--postprocessor-args",
            "ffmpeg:-bitexact",
            "--max-filesize",
            "1000M",  # Limit to 1GB per video
        ]
        *_, validated_options = yt_dlp.parse_options(ydl_options)
        downloaded = 0
        with yt_dlp.YoutubeDL(validated_options) as ydl:
            for url in video_urls:
                try:
                    logger.debug(f"Downloading video from URL: {url}")
                    info = ydl.extract_info(url, download=True)
                    filename = ydl_entry_to_filename(ydl, info)
                    if not filename:  # Failed to download video.
                        continue
                    media = Media(filename)
                    for x in ["duration", "original_url", "fulltitle", "description", "upload_date"]:
                        if x in info:
                            media.set(x, info[x])
                    to_enrich.add_media(media)
                    downloaded += 1
                except Exception as e:
                    logger.error(f"Error downloading {url}: {e}")
        return downloaded
