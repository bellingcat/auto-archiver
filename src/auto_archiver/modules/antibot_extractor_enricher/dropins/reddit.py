from contextlib import suppress
from typing import Mapping
from auto_archiver.core.metadata import Metadata
from auto_archiver.modules.antibot_extractor_enricher.dropin import Dropin

from auto_archiver.utils.custom_logger import logger


class RedditDropin(Dropin):
    """
    A class to handle Reddit drop-in functionality for the antibot extractor enricher module.
    """

    def documentation() -> Mapping[str, str]:
        return {
            "name": "Reddit Dropin",
            "description": "Handles Reddit posts and works without authentication until Reddit flags your IP, so authentication is advised.",
            "site": "reddit.com",
            "authentication": {
                "reddit.com": {
                    "username": "email address or username",
                    "password": "password",
                }
            },
        }

    @staticmethod
    def suitable(url: str) -> bool:
        return "reddit.com" in url

    @staticmethod
    def images_selectors() -> str:
        return "shreddit-post img"

    @staticmethod
    def video_selectors() -> str:
        return "shreddit-post video, shreddit-post source"

    def open_page(self, url) -> bool:
        if self.sb.is_text_visible("You've been blocked by network security."):
            self._login()
            if url != self.sb.get_current_url():
                self.sb.open(url)
        return True

    @logger.catch
    def _login(self):
        self.sb.click_link_text("Log in")
        self.sb.wait_for_ready_state_complete()
        self._close_cookies_banner()

        username, password = self._get_username_password("reddit.com")
        logger.debug("Logging in to Reddit with username: {}", username)

        self.sb.type("#login-username", username)
        self.sb.type("#login-password", password)

        elem = self.sb.find_element("button.login")
        self.sb.execute_script("arguments[0].scrollIntoView(true);", elem)
        self.sb.slow_click("button.login")
        self.sb.wait_for_ready_state_complete()

        if "https://www.reddit.com/login/" in self.sb.get_current_url():
            self.sb.sleep(5)
            self.sb.wait_for_ready_state_complete()

        if self.sb.is_text_visible("You've been blocked by network security."):
            self.sb.click_link_text("Log in")
            self.sb.wait_for_ready_state_complete()
            if self.sb.is_text_visible("Welcome back"):
                logger.debug("Login successful")
                self.sb.click_if_visible("this link")

    def _close_cookies_banner(self):
        with suppress(Exception):  # selenium.common.exceptions.JavascriptException
            self.sb.execute_script("""
                document
                    .querySelector("reddit-cookie-banner")
                    .shadowRoot.querySelector("faceplate-dialog")
                    .querySelector("#accept-all-cookies-button button")
                    .click()
            """)

    @logger.catch
    def add_extra_media(self, to_enrich: Metadata) -> tuple[int, int]:
        filtered_urls = self.sb.execute_script(rf"""
            return [...document.querySelectorAll("{self.video_selectors()}")]
            .map(el => el.src || el.href)
            .filter(url => url && /\.(m3u8|mpd|ism)$/.test(url));
        """)
        logger.debug("Found {} video URLs", len(filtered_urls))
        return 0, self._download_videos_with_ytdlp(filtered_urls, to_enrich)
