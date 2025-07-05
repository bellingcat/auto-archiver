from contextlib import suppress
from typing import Mapping
from auto_archiver.modules.antibot_extractor_enricher.dropin import Dropin


class TikTokDropin(Dropin):
    """
    A class to handle TikTok drop-in functionality for the antibot extractor enricher module.
    """

    def documentation() -> Mapping[str, str]:
        return {
            "name": "TikTok Dropin",
            "description": "Handles TikTok posts and works without authentication.",
            "site": "tiktok.com",
        }

    @staticmethod
    def suitable(url: str) -> bool:
        return "tiktok.com" in url

    @staticmethod
    def images_selectors() -> str:
        return '[data-e2e="detail-photo"] img'

    @staticmethod
    def video_selectors() -> str:
        return None  # TikTok videos should be handled by the generic extractor

    def open_page(self, url) -> bool:
        self.sb.wait_for_ready_state_complete()
        self._close_cookies_banner()
        # TODO: implement login logic
        if url != self.sb.get_current_url():
            return False
        return True

    def hit_auth_wall(self) -> bool:
        return False  # TikTok does not require authentication for public posts

    def _close_cookies_banner(self):
        with suppress(Exception):  # selenium.common.exceptions.JavascriptException
            self.sb.execute_script("""
                document
                    .querySelector("tiktok-cookie-banner")
                    .shadowRoot.querySelector("faceplate-dialog")
                    .querySelector("button")
                    .click()
            """)
        self.sb.click_if_visible("Skip")
