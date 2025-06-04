import pytest

from auto_archiver.modules.antibot_extractor_enricher.antibot_extractor_enricher import AntibotExtractorEnricher
from .test_extractor_base import TestExtractorBase


class DummySB:
    def __init__(self, url="", title="", visible_texts=None, visible_elements=None):
        self._url = url
        self._title = title
        self._visible_texts = visible_texts or set()
        self._visible_elements = visible_elements or set()

    def get_current_url(self):
        return self._url

    def get_title(self):
        return self._title

    def is_text_visible(self, text):
        return text in self._visible_texts

    def is_element_visible(self, selector):
        return selector in self._visible_elements


class TestAntibotExtractorEnricher(TestExtractorBase):
    """Tests Antibot Extractor/Enricher"""

    extractor_module = "antibot_extractor_enricher"
    extractor: AntibotExtractorEnricher

    config = {
        "save_to_pdf": False,
        "max_download_images": 0,
        "max_download_videos": 0,
        "exclude_media_extensions": ".svg,.ico,.gif",
        "proxy": None,
    }

    @pytest.mark.download
    @pytest.mark.parametrize(
        "url,in_title,image_count,video_count",
        [
            (
                "https://en.wikipedia.org/wiki/Western_barn_owl",
                "western barn owl",
                5,
                0,
            ),
            (
                "https://www.bellingcat.com/news/2025/04/29/open-sources-show-myanmar-junta-airstrike-damages-despite-post-earthquake-ceasefire/",
                "open sources show myanmar",
                5,
                0,
            ),
            (
                "https://www.bellingcat.com/news/2025/03/27/gaza-israel-palestine-shot-killed-injured-destroyed-dangerous-drone-journalists-in-gaza/",
                "shot from above",
                5,
                1,
            ),
            (
                "https://www.bellingcat.com/about/general-information",
                "general information",
                0,  # SVGs are ignored
                0,
            ),
        ],
    )
    def test_download_pages_with_media(self, setup_module, make_item, url, in_title, image_count, video_count):
        """
        Test downloading pages with media.
        """

        self.extractor = setup_module(
            self.extractor_module,
            {
                "save_to_pdf": True,
                "max_download_images": 5,
                "max_download_videos": "inf",
            },
        )

        item = make_item(url)
        result = self.extractor.download(item)

        assert result.status == "antibot", "Expected status to be 'antibot'"

        # Check title contains all required words (case-insensitive)
        page_title = result.get_title() or ""
        assert in_title in page_title.lower(), f"Expected title to contain '{in_title}', got '{page_title}'"

        image_media = [m for m in result.media if m.is_image() and not m.get("id") == "screenshot"]
        assert len(image_media) == image_count, f"Expected {image_count} image items, got {len(image_media)}"
        video_media = [m for m in result.media if m.is_video()]
        assert len(video_media) == video_count, f"Expected {video_count} video items, got {len(video_media)}"

        for expected_id in ["screenshot", "pdf", "html_source_code"]:
            assert any(m.get("id") == expected_id for m in result.media), (
                f"Expected media with id '{expected_id}' not found"
            )

    @pytest.mark.download
    @pytest.mark.parametrize(
        "url,in_html",
        [
            (
                "https://myrotvorets.center/about/",
                "Центр «Миротворець»",
            ),
            (
                "https://seleniumbase.io/apps/turnstile",
                'id="captcha-success"',
            ),
        ],
    )
    def test_download_with_cloudflare_turnstile(self, setup_module, make_item, url, in_html):
        """
        Test downloading a page with Cloudflare Turnstile captcha.
        """

        item = make_item(url)
        self.extractor.enrich(item)

        assert item.status != "antibot", "Expected status not to be 'antibot' after handling Cloudflare Turnstile"

        html_media = item.get_media_by_id("html_source_code")
        with open(html_media.filename, "r", encoding="utf-8") as f:
            html_content = f.read()
            assert in_html.lower() in html_content.lower(), f"Expected HTML to contain '{in_html}'"

    @pytest.mark.parametrize(
        "url,title,visible_texts,visible_elements,expected",
        [
            # URL triggers
            ("https://example.com/login", "Welcome", set(), set(), True),
            ("https://example.com/somepage", "Just a moment...", set(), set(), True),
            ("https://example.com/", "Welcome", {"Please log in"}, set(), True),
            ("https://example.com/", "Welcome", set(), {"input[type='password']"}, True),
            ("https://example.com/", "Welcome", set("No issue here"), set(), False),
            # Title triggers
            ("https://example.com/", "Log in", set(), set(), True),
            ("https://example.com/", "Verification required", set(), set(), True),
            # Text triggers (case-insensitive)
            ("https://example.com/", "Welcome", {"Sign up or log in"}, set(), True),
            ("https://example.com/", "Welcome", {"sign up or log in"}, set(), True),
            # Element triggers
            ("https://example.com/", "Welcome", set(), {"input[name='email']"}, True),
            # No triggers
            ("https://example.com/", "Welcome", set(), set(), False),
        ],
    )
    def test_hit_auth_wall(self, url, title, visible_texts, visible_elements, expected):
        extractor = AntibotExtractorEnricher()
        sb = DummySB(url=url, title=title, visible_texts=visible_texts, visible_elements=visible_elements)
        assert extractor._hit_auth_wall(sb) == expected

    def test_enrich_handles_sb_exception(self, make_item, mocker):
        """
        Test that enrich returns False and logs error if SB raises an exception.
        """

        # Patch SB to raise an exception on context enter
        mock_sb = mocker.patch("auto_archiver.modules.antibot_extractor_enricher.antibot_extractor_enricher.SB")
        mock_logger = mocker.patch("auto_archiver.modules.antibot_extractor_enricher.antibot_extractor_enricher.logger")
        mock_sb.side_effect = Exception("SB failed")

        item = make_item("https://example.com/")
        result = self.extractor.enrich(item)

        assert result is False
        mock_logger.error.assert_called()
