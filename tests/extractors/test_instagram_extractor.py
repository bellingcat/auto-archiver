import pytest

from auto_archiver.modules.instagram_extractor import InstagramExtractor
from .test_extractor_base import TestExtractorBase


@pytest.fixture
def intsagram_extractor(setup_module):

    extractor_module: str = 'instagram_extractor'
    config: dict = {
        "username": "user_name",
        "password": "password123",
        "download_folder": "instaloader",
        "session_file": "secrets/instaloader.session",
    }
    return setup_module(extractor_module, config)




@pytest.mark.parametrize("url", [
    "https://www.instagram.com/p/",
    "https://www.instagram.com/p/1234567890/",
    "https://www.instagram.com/reel/1234567890/",
    "https://www.instagram.com/username/",
    "https://www.instagram.com/username/stories/",
    "https://www.instagram.com/username/highlights/",
])
def test_regex_matches(url, instagram_extractor):
    # post
    assert  instagram_extractor.valid_url.match(url)
