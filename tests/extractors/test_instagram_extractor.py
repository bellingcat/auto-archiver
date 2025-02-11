import pytest

from auto_archiver.modules.instagram_extractor import InstagramExtractor
from .test_extractor_base import TestExtractorBase

class TestInstagramExtractor(TestExtractorBase):

    extractor_module: str = 'instagram_extractor'
    config: dict = {}

    @pytest.mark.parametrize("url", [
        "https://www.instagram.com/p/",
        "https://www.instagram.com/p/1234567890/",
        "https://www.instagram.com/reel/1234567890/",
        "https://www.instagram.com/username/",
        "https://www.instagram.com/username/stories/",
        "https://www.instagram.com/username/highlights/",
    ])
    def test_regex_matches(self, url):
        # post
        assert InstagramExtractor.valid_url.match(url)
