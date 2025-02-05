from datetime import datetime
from typing import Type

import pytest
from unittest.mock import patch, MagicMock

from auto_archiver.core import Metadata
from auto_archiver.modules.instagram_api_extractor.instagram_api_extractor import InstagramAPIExtractor
from .test_extractor_base import TestExtractorBase


@pytest.fixture
def mock_user_response():
    return {
        "user": {
            "pk": "123",
            "username": "test_user",
            "full_name": "Test User",
            "profile_pic_url_hd": "http://example.com/profile.jpg",
            "profile_pic_url": "http://example.com/profile_lowres.jpg"
        }
    }

@pytest.fixture
def mock_post_response():
    return {
        "id": "post_123",
        "code": "abc123",
        "caption_text": "Test Caption",
        "taken_at": datetime.now().timestamp(),
        "video_url": "http://example.com/video.mp4",
        "thumbnail_url": "http://example.com/thumbnail.jpg"
    }

@pytest.fixture
def mock_story_response():
    return [{
        "id": "story_123",
        "taken_at": datetime.now().timestamp(),
        "video_url": "http://example.com/story.mp4"
    }]

@pytest.fixture
def mock_highlight_response():
    return {
        "response": {
            "reels": {
                "highlight:123": {
                    "id": "123",
                    "title": "Test Highlight",
                    "items": [{
                        "id": "item_123",
                        "taken_at": datetime.now().timestamp(),
                        "video_url": "http://example.com/highlight.mp4"
                    }]
                }
            }
        }
    }


# @pytest.mark.incremental
class TestInstagramAPIExtractor(TestExtractorBase):
    """
    Test suite for InstagramAPIExtractor.
    """

    extractor_module = "instagram_api_extractor"
    extractor: InstagramAPIExtractor

    config = {
        "access_token": "test_access_token",
        "api_endpoint": "https://api.instagram.com/v1",
        # "full_profile": False,
        # "full_profile_max_posts": 0,
        # "minimize_json_output": True,
    }

    @pytest.mark.parametrize("url,expected", [
        ("https://instagram.com/user", [("", "user", "")]),
        ("https://instagr.am/p/post_id", []),
        ("https://youtube.com", []),
        ("https://www.instagram.com/reel/reel_id", [("reel", "reel_id", "")]),
        ("https://instagram.com/stories/highlights/123", [("stories/highlights", "123", "")]),
        ("https://instagram.com/stories/user/123", [("stories", "user", "123")]),
    ])
    def test_url_parsing(self, url, expected):
        assert self.extractor.valid_url.findall(url) == expected

    def test_initialize(self):
        self.extractor.initialise()
        assert self.extractor.api_endpoint[-1] != "/"

    @pytest.mark.parametrize("input_dict,expected", [
        ({"x": 0, "valid": "data"}, {"valid": "data"}),
        ({"nested": {"y": None, "valid": [{}]}}, {"nested": {"valid": [{}]}}),
    ])
    def test_cleanup_dict(self, input_dict, expected):
        assert self.extractor.cleanup_dict(input_dict) == expected

    def test_download_post(self):
        # test with context=reel
        # test with context=post
        # test with multiple images
        # test gets text (metadata title)


        pass