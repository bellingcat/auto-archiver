from datetime import datetime
import math

import pytest

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
            "profile_pic_url": "http://example.com/profile_lowres.jpg",
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
        "thumbnail_url": "http://example.com/thumbnail.jpg",
    }


@pytest.fixture
def mock_story_response():
    return [{"id": "story_123", "taken_at": datetime.now().timestamp(), "video_url": "http://example.com/story.mp4"}]


@pytest.fixture
def mock_highlight_response():
    return {
        "response": {
            "reels": {
                "highlight:123": {
                    "id": "123",
                    "title": "Test Highlight",
                    "items": [
                        {
                            "id": "item_123",
                            "taken_at": datetime.now().timestamp(),
                            "video_url": "http://example.com/highlight.mp4",
                        }
                    ],
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
        "full_profile": False,
        # "full_profile_max_posts": 0,
        # "minimize_json_output": True,
    }

    @pytest.fixture
    def metadata(self):
        m = Metadata()
        m.set_url("https://instagram.com/test_user")
        m.set("netloc", "instagram.com")
        return m

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://instagram.com/user", [("", "user", "")]),
            ("https://instagr.am/p/post_id", []),
            ("https://youtube.com", []),
            ("https://www.instagram.com/reel/reel_id", [("reel", "reel_id", "")]),
            ("https://instagram.com/stories/highlights/123", [("stories/highlights", "123", "")]),
            ("https://instagram.com/stories/user/123", [("stories", "user", "123")]),
        ],
    )
    def test_url_parsing(self, url, expected):
        assert self.extractor.valid_url.findall(url) == expected

    def test_initialize(self):
        assert self.extractor.api_endpoint[-1] != "/"

    @pytest.mark.parametrize(
        "input_dict,expected",
        [
            ({"x": 0, "valid": "data"}, {"valid": "data"}),
            ({"nested": {"y": None, "valid": [{}]}}, {"nested": {"valid": [{}]}}),
        ],
    )
    def test_cleanup_dict(self, input_dict, expected):
        assert self.extractor.cleanup_dict(input_dict) == expected

    def test_download(self):
        pass

    def test_download_post(self, metadata, mock_user_response):
        # test with context=reel
        # test with context=post
        # test with multiple images
        # test gets text (metadata title)
        pass

    def test_download_profile_basic(self, metadata, mock_user_response, mocker):
        """Test basic profile download without full_profile"""
        mock_call = mocker.patch.object(self.extractor, "call_api")
        mock_download = mocker.patch.object(self.extractor, "download_from_url")
        # Mock API responses
        mock_call.return_value = mock_user_response
        mock_download.return_value = "profile.jpg"

        result = self.extractor.download_profile(metadata, "test_user")
        assert result.status == "insta profile: success"
        assert result.get_title() == "Test User"
        assert result.get("data") == self.extractor.cleanup_dict(mock_user_response["user"])
        # Verify profile picture download
        mock_call.assert_called_once_with("v2/user/by/username", {"username": "test_user"})
        mock_download.assert_called_once_with("http://example.com/profile.jpg")
        assert len(result.media) == 1
        assert result.media[0].filename == "profile.jpg"

    def test_download_profile_full(self, metadata, mock_user_response, mock_story_response, mocker):
        """Test full profile download with stories/posts"""
        mock_call = mocker.patch.object(self.extractor, "call_api")
        mock_posts = mocker.patch.object(self.extractor, "download_all_posts")
        mock_highlights = mocker.patch.object(self.extractor, "download_all_highlights")
        mock_tagged = mocker.patch.object(self.extractor, "download_all_tagged")
        mock_stories = mocker.patch.object(self.extractor, "_download_stories_reusable")

        self.extractor.full_profile = True
        mock_call.side_effect = [mock_user_response, mock_story_response]
        mock_highlights.return_value = 1
        mock_stories.return_value = mock_story_response
        mock_posts.return_value = 2
        mock_tagged.return_value = 3

        result = self.extractor.download_profile(metadata, "test_user")
        assert result.get("#stories") == len(mock_story_response)
        mock_posts.assert_called_once_with(result, "123", max_to_download=math.inf)
        assert "errors" not in result.metadata

    def test_download_profile_not_found(self, metadata, mocker):
        """Test profile not found error"""
        mock_call = mocker.patch.object(self.extractor, "call_api")
        mock_call.return_value = {"user": None}
        with pytest.raises(AssertionError) as exc_info:
            self.extractor.download_profile(metadata, "invalid_user")
        assert "User invalid_user not found" in str(exc_info.value)

    def test_download_profile_error_handling(self, metadata, mock_user_response, mocker):
        """Test error handling in full profile mode"""
        mock_call = mocker.patch.object(self.extractor, "call_api")
        mock_highlights = mocker.patch.object(self.extractor, "download_all_highlights")
        mock_tagged = mocker.patch.object(self.extractor, "download_all_tagged")
        stories_tagged = mocker.patch.object(self.extractor, "_download_stories_reusable")
        mock_posts = mocker.patch.object(self.extractor, "download_all_posts")

        self.extractor.full_profile = True
        mock_call.side_effect = [mock_user_response, Exception("Stories API failed"), Exception("Posts API failed")]
        mock_highlights.return_value = 1
        mock_tagged.return_value = 2
        stories_tagged.return_value = None
        mock_posts.return_value = 4
        result = self.extractor.download_profile(metadata, "test_user")

        assert result.is_success()
        assert "Error downloading stories for test_user" in result.metadata["errors"]
