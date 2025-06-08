import os
import re

from auto_archiver.core.media import Media
from auto_archiver.core.metadata import Metadata
from auto_archiver.modules.antibot_extractor_enricher.dropin import Dropin
from auto_archiver.utils.misc import ydl_entry_to_filename

import yt_dlp
from loguru import logger


class VkDropin(Dropin):
    """
    A class to handle VK drop-in functionality for the antibot extractor enricher module.
    """

    WALL_PATTERN = re.compile(r"(wall.{0,1}\d+_\d+)")
    VIDEO_PATTERN = re.compile(r"(video.{0,1}\d+_\d+(?:_\w+)?)")
    CLIP_PATTERN = re.compile(r"(clip.{0,1}\d+_\d+)")
    PHOTO_PATTERN = re.compile(r"(photo.{0,1}\d+_\d+)")

    @staticmethod
    def suitable(url: str) -> bool:
        return "vk.com" in url

    @staticmethod
    def sanitize_url(url: str) -> str:
        """
        Transforms modal URLs like 'https://vk.com/page_name?w=wall-123456_7890' to 'https://vk.com/wall-123456_7890'
        """
        for pattern in [VkDropin.WALL_PATTERN, VkDropin.VIDEO_PATTERN, VkDropin.CLIP_PATTERN, VkDropin.PHOTO_PATTERN]:
            match = pattern.search(url)
            if match:
                return f"https://vk.com/{match.group(1)}"
        return url

    def open_page(self, url) -> bool:
        if self.sb.is_text_visible("Sign in to VK"):
            self._login()
            self.sb.open(url)
        return True

    def _login(self) -> bool:
        # TODO: test method
        self.sb.open("https://vk.com")
        self.sb.wait_for_ready_state_complete()
        if "/feed" in self.sb.get_current_url():
            logger.debug("Already logged in to VK.")
            return True

        # need to login
        logger.debug("Logging in to VK...")
        auth = self.extractor.auth_for_site("vk.com")
        username = auth.get("username", "")
        password = auth.get("password", "")
        if not username or not password:
            raise ValueError("VK authentication requires a username and password.")
        logger.debug("Using username: {}", username)
        self.sb.click('[data-testid="enter-another-way"]', timeout=10)
        self.sb.clear('input[name="login"][type="tel"]', by="css selector", timeout=10)
        self.sb.type('input[name="login"][type="tel"]', username, by="css selector", timeout=10)
        self.sb.click('button[type="submit"]')

        # TODO: handle captcha if it appears
        # if sb.is_element_visible("img.vkc__CaptchaPopup__image"):
        #     captcha_url = sb.get_attribute("img.vkc__CaptchaPopup__image", "src")
        #     print("CAPTCHA detected:", captcha_url)
        #     image_url = sb.get_attribute("img[alt*='captcha']", "src")
        #     solution = solve_captcha(image_url)
        #     sb.type("input#captcha-text, input[name='captcha']", solution)
        #     sb.click("button[type='submit']")

        self.sb.type('input[name="password"]', password, timeout=15)
        self.sb.click('button[type="submit"]')
        self.sb.wait_for_ready_state_complete(timeout=10)
        self.sb.wait_for_element("body", timeout=10)
        # self.sb.sleep(2)
        return "/feed" in self.sb.get_current_url()

    @logger.catch
    def add_extra_media(self, to_enrich: Metadata) -> tuple[int, int]:
        """
        Extract video data from the currently open post with SeleniumBase.

        :return: A tuple (number of Images added, number of Videos added).
        """
        video_urls = [v.get_attribute("href") for v in self.sb.find_elements('a[href*="/video-"]')]
        if type(self.extractor.max_download_videos) is int:
            video_urls = video_urls[: self.extractor.max_download_videos]

        if not video_urls:
            return 0, 0

        logger.debug(f"Found {len(video_urls)} video URLs in the post, using ytdlp for download.")
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
        return 0, downloaded
