"""
Tests for the Twitter dropin extractor with fxtwitter fallback
"""

import pytest
from unittest.mock import Mock, patch

from auto_archiver.modules.generic_extractor.twitter import Twitter


@pytest.fixture
def twitter_dropin():
    return Twitter()


class TestTwitterFxTwitterFallback:
    """Test the fxtwitter API fallback functionality."""

    @pytest.fixture
    def mock_fxtwitter_video_response(self):
        return {
            "code": 200,
            "message": "OK",
            "tweet": {
                "url": "https://x.com/user/status/123456789",
                "id": "123456789",
                "text": "Test tweet with video",
                "author": {
                    "id": "111",
                    "name": "Test User",
                    "screen_name": "testuser",
                },
                "created_at": "Sun Feb 08 18:45:00 +0000 2026",
                "media": {
                    "all": [
                        {
                            "type": "video",
                            "url": "https://video.twimg.com/test.mp4",
                            "variants": [
                                {"url": "https://video.twimg.com/test.m3u8", "content_type": "application/x-mpegURL"},
                                {
                                    "url": "https://video.twimg.com/test_480.mp4",
                                    "content_type": "video/mp4",
                                    "bitrate": 632000,
                                },
                                {
                                    "url": "https://video.twimg.com/test_720.mp4",
                                    "content_type": "video/mp4",
                                    "bitrate": 2176000,
                                },
                            ],
                        }
                    ],
                    "videos": [
                        {
                            "url": "https://video.twimg.com/test.mp4",
                            "variants": [
                                {"url": "https://video.twimg.com/test.m3u8", "content_type": "application/x-mpegURL"},
                                {
                                    "url": "https://video.twimg.com/test_480.mp4",
                                    "content_type": "video/mp4",
                                    "bitrate": 632000,
                                },
                                {
                                    "url": "https://video.twimg.com/test_720.mp4",
                                    "content_type": "video/mp4",
                                    "bitrate": 2176000,
                                },
                            ],
                        }
                    ],
                },
            },
        }

    @pytest.fixture
    def mock_fxtwitter_photo_response(self):
        return {
            "code": 200,
            "message": "OK",
            "tweet": {
                "url": "https://x.com/user/status/123456790",
                "id": "123456790",
                "text": "Test tweet with photo",
                "author": {
                    "id": "111",
                    "name": "Test User",
                    "screen_name": "testuser",
                },
                "created_at": "Mon Feb 09 10:30:00 +0000 2026",
                "media": {
                    "all": [
                        {
                            "type": "photo",
                            "url": "https://pbs.twimg.com/media/test.jpg?name=orig",
                        }
                    ],
                    "photos": [
                        {
                            "type": "photo",
                            "url": "https://pbs.twimg.com/media/test.jpg?name=orig",
                        }
                    ],
                },
            },
        }

    def test_fetch_fxtwitter_video(self, twitter_dropin, mock_fxtwitter_video_response):
        """Test fetching a tweet with video via fxtwitter API."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_fxtwitter_video_response
            mock_get.return_value = mock_response

            result = twitter_dropin._fetch_fxtwitter("123456789")

            assert result["user"]["name"] == "Test User"
            assert result["created_at"] == "Sun Feb 08 18:45:00 +0000 2026"
            assert result["full_text"] == "Test tweet with video"
            assert len(result["entities"]["media"]) == 1
            assert result["entities"]["media"][0]["type"] == "video"
            assert "video_info" in result["entities"]["media"][0]
            assert len(result["entities"]["media"][0]["video_info"]["variants"]) == 3

    def test_fetch_fxtwitter_photo(self, twitter_dropin, mock_fxtwitter_photo_response):
        """Test fetching a tweet with photo via fxtwitter API."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_fxtwitter_photo_response
            mock_get.return_value = mock_response

            result = twitter_dropin._fetch_fxtwitter("123456790")

            assert result["user"]["name"] == "Test User"
            assert result["created_at"] == "Mon Feb 09 10:30:00 +0000 2026"
            assert result["full_text"] == "Test tweet with photo"
            assert len(result["entities"]["media"]) == 1
            assert result["entities"]["media"][0]["type"] == "photo"
            assert result["entities"]["media"][0]["media_url_https"] == "https://pbs.twimg.com/media/test.jpg?name=orig"

    def test_fetch_fxtwitter_no_media(self, twitter_dropin):
        """Test fetching a text-only tweet via fxtwitter API."""
        mock_response_data = {
            "code": 200,
            "message": "OK",
            "tweet": {
                "id": "123456791",
                "text": "Just text, no media",
                "author": {"name": "Text Only User"},
                "created_at": "Tue Feb 10 12:00:00 +0000 2026",
                "media": {},
            },
        }
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            result = twitter_dropin._fetch_fxtwitter("123456791")

            assert result["user"]["name"] == "Text Only User"
            assert result["full_text"] == "Just text, no media"
            assert result["entities"]["media"] == []

    def test_fetch_fxtwitter_api_error(self, twitter_dropin):
        """Test handling of fxtwitter API errors."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            with pytest.raises(Exception):
                twitter_dropin._fetch_fxtwitter("nonexistent")


class TestTwitterChooseVariant:
    """Test the video variant selection logic."""

    def test_choose_highest_quality_video(self, twitter_dropin):
        """Test that the highest quality video variant is selected."""
        variants = [
            {"url": "https://video.twimg.com/vid/320x240/test.mp4", "content_type": "video/mp4"},
            {"url": "https://video.twimg.com/vid/1280x720/test.mp4", "content_type": "video/mp4"},
            {"url": "https://video.twimg.com/vid/640x480/test.mp4", "content_type": "video/mp4"},
        ]

        result = twitter_dropin.choose_variant(variants)

        assert result["url"] == "https://video.twimg.com/vid/1280x720/test.mp4"

    def test_choose_variant_fallback_for_non_mp4(self, twitter_dropin):
        """Test fallback when no mp4 variant is available."""
        variants = [
            {"url": "https://video.twimg.com/test.m3u8", "content_type": "application/x-mpegURL"},
        ]

        result = twitter_dropin.choose_variant(variants)

        assert result["url"] == "https://video.twimg.com/test.m3u8"

    def test_choose_variant_prefers_mp4(self, twitter_dropin):
        """Test that mp4 is preferred over other formats when quality is equal."""
        variants = [
            {"url": "https://video.twimg.com/test.m3u8", "content_type": "application/x-mpegURL"},
            {"url": "https://video.twimg.com/vid/1280x720/test.mp4", "content_type": "video/mp4"},
        ]

        result = twitter_dropin.choose_variant(variants)

        assert result["content_type"] == "video/mp4"


@pytest.mark.download
class TestTwitterFxTwitterLive:
    """Live integration tests for fxtwitter API - requires network access."""

    @pytest.mark.parametrize(
        "tweet_id,expected_media_type",
        [
            ("2020569571682312581", "video"),  # Video tweet
            ("2020410438198890618", "video"),  # Video tweet
            ("2020341585502957801", "photo"),  # Photo tweet
        ],
    )
    def test_fetch_real_tweets(self, twitter_dropin, tweet_id, expected_media_type):
        """Test fetching real tweets from fxtwitter API."""
        result = twitter_dropin._fetch_fxtwitter(tweet_id)

        assert result["user"]["name"]  # Author should be non-empty
        assert result["created_at"]  # Should have timestamp
        assert result["full_text"]  # Should have text content

        media = result["entities"]["media"]
        assert len(media) >= 1
        assert media[0]["type"] == expected_media_type
