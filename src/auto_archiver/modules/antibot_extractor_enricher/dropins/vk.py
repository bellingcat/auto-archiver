import re
from typing import Mapping

from auto_archiver.core.metadata import Metadata
from auto_archiver.modules.antibot_extractor_enricher.dropin import Dropin

from auto_archiver.utils.custom_logger import logger


class VkDropin(Dropin):
    """
    A class to handle VK drop-in functionality for the antibot extractor enricher module.
    """

    WALL_PATTERN = re.compile(r"(wall.{0,1}\d+_\d+)")
    VIDEO_PATTERN = re.compile(r"(video.{0,1}\d+_\d+(?:_\w+)?)")
    CLIP_PATTERN = re.compile(r"(clip.{0,1}\d+_\d+)")
    PHOTO_PATTERN = re.compile(r"(photo.{0,1}\d+_\d+)")

    def documentation() -> Mapping[str, str]:
        return {
            "name": "VKontakte Dropin",
            "description": "Handles VKontakte posts and works without authentication for some content.",
            "site": "vk.com",
            "authentication": {
                "vk.com": {
                    "username": "phone number with country code",
                    "password": "password",
                }
            },
        }

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
            if self._login():
                self.sb.open(url)
        return True

    @logger.catch
    def _login(self) -> bool:
        # TODO: test method, because current tests work without a login
        self.sb.open("https://vk.com")
        self.sb.wait_for_ready_state_complete()
        if "/feed" in self.sb.get_current_url():
            logger.debug("Already logged in to VK.")
            return True

        # need to login
        username, password = self._get_username_password("vk.com")
        logger.debug("Logging in to VK with username: {}", username)

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
        video_urls = [v.get_attribute("href") for v in self.sb.find_elements('a[href*="/video-"]')]

        return 0, self._download_videos_with_ytdlp(video_urls, to_enrich)
