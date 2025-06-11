from loguru import logger
from auto_archiver.modules.antibot_extractor_enricher.dropin import Dropin


class LinkedinDropin(Dropin):
    """
    A class to handle LinkedIn drop-in functionality for the antibot extractor enricher module.
    """

    notifications_css_selector = 'a[href*="linkedin.com/notifications"]'

    @staticmethod
    def suitable(url: str) -> bool:
        return "linkedin.com" in url

    def js_for_image_css_selectors(self) -> str:
        get_all_css = "main img:not([src*='profile-displayphoto']):not([src*='profile-framedphoto'])"
        get_first_css = (
            "main img[src*='profile-framedphoto'], main img[src*='profile-displayphoto'], main img[src*='company-logo']"
        )

        return f"""
            const all = Array.from(document.querySelectorAll("{get_all_css}")).map(el => el.src || el.href).filter(Boolean);
            const profile = document.querySelector("{get_first_css}");
            return all.concat(profile?.src || profile?.href || []).filter(Boolean);
        """

    @staticmethod
    def video_selectors() -> str:
        # usually videos are from blob: but running the generic extractor should handle that
        return "main video"

    def open_page(self, url) -> bool:
        if not self.sb.is_element_present(self.notifications_css_selector):
            self._login()
            if url != self.sb.get_current_url():
                self.sb.open(url)
        return True

    @logger.catch
    def _login(self) -> bool:
        if self.sb.is_text_visible("Sign in to view more content"):
            self.sb.click_link_text("Sign in", timeout=2)
            self.sb.wait_for_ready_state_complete()
        else:
            self.sb.open("https://www.linkedin.com/login")
            self.sb.wait_for_ready_state_complete()

        username, password = self._get_username_password("linkedin.com")
        logger.debug("LinkedinDropin Logging in to Linkedin with username: {}", username)
        self.sb.type("#username", username)
        self.sb.type("#password", password)
        self.sb.click_if_visible("#password-visibility-toggle", timeout=0.5)
        self.sb.click("button[type='submit']")
        self.sb.wait_for_ready_state_complete()
        # TODO: on suspicious login, LinkedIn may require an email verification code

        if not self.sb.is_element_present(self.notifications_css_selector):
            self.sb.click_if_visible('button[aria-label="Dismiss"]', timeout=0.5)
