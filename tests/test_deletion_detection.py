"""
Tests for deletion detection utilities.

These tests verify that the auto-archiver can detect when content
has been deleted or is unavailable across various platforms.
Critical for evidence preservation in conflict documentation.
"""

import pytest
from auto_archiver.utils.deletion_detection import (
    detect_deletion,
    flag_as_deleted,
    DeletionIndicators
)
from auto_archiver.core.metadata import Metadata


class TestDeletionIndicators:
    """Test the deletion indicator lists for various platforms."""

    def test_twitter_indicators(self):
        """Verify Twitter deletion indicators are comprehensive."""
        assert "Hmm...this page doesn't exist" in DeletionIndicators.TWITTER
        assert "Try searching for something else" in DeletionIndicators.TWITTER
        assert "This Tweet is unavailable" in DeletionIndicators.TWITTER

    def test_platform_specific_indicators(self):
        """Test that platform-specific indicators are returned based on URL."""
        twitter_indicators = DeletionIndicators.for_url("https://twitter.com/user/status/123")
        assert any("page doesn't exist" in ind.lower() for ind in twitter_indicators)

        instagram_indicators = DeletionIndicators.for_url("https://instagram.com/p/ABC123")
        assert any("page isn't available" in ind.lower() for ind in instagram_indicators)


class TestDetectDeletion:
    """Test the detect_deletion function with various inputs."""

    def test_detect_deletion_in_html_twitter(self):
        """Test detection of Twitter's deleted post page."""
        html = "<html><body>Hmm...this page doesn't exist. Try searching for something else.</body></html>"
        url = "https://twitter.com/user/status/123"

        result = detect_deletion(html_content=html, url=url)

        assert result is not None
        assert result["is_deleted"] is True
        assert result["platform"] == "twitter"
        assert result["source"] == "html_content"
        assert "page doesn't exist" in result["indicator"].lower()

    def test_detect_deletion_in_page_title(self):
        """Test detection via page title."""
        title = "Page Not Found"
        url = "https://facebook.com/post/123"

        result = detect_deletion(page_title=title, url=url)

        assert result is not None
        assert result["is_deleted"] is True
        assert result["source"] == "page_title"

    def test_detect_deletion_in_error_message(self):
        """Test detection via error messages."""
        error = "yt_dlp.utils.DownloadError: This video is no longer available"
        url = "https://youtube.com/watch?v=abc123"

        result = detect_deletion(error_message=error, url=url)

        assert result is not None
        assert result["is_deleted"] is True
        assert result["platform"] == "youtube"
        assert result["source"] == "error_message"

    def test_detect_deletion_in_video_metadata(self):
        """Test detection via yt-dlp video metadata."""
        video_data = {
            "availability": "unavailable",
            "title": "Private video"
        }
        url = "https://youtube.com/watch?v=test123"

        result = detect_deletion(video_data=video_data, url=url)

        assert result is not None
        assert result["is_deleted"] is True
        assert result["source"] == "video_metadata"
        assert "availability" in result["indicator"]

    def test_no_deletion_detected(self):
        """Test that normal content is not flagged as deleted."""
        html = "<html><body><h1>Welcome to my page</h1><p>This is normal content.</p></body></html>"
        title = "My Normal Page"
        url = "https://example.com/page"

        result = detect_deletion(
            html_content=html,
            page_title=title,
            url=url
        )

        assert result is None

    def test_instagram_media_not_found(self):
        """Test Instagram-specific deletion message."""
        error = "Media not found or unavailable"
        url = "https://instagram.com/p/ABC123"

        result = detect_deletion(error_message=error, url=url)

        assert result is not None
        assert result["platform"] == "instagram"
        assert "not found" in result["indicator"].lower()

    def test_reddit_removed_content(self):
        """Test Reddit [removed] and [deleted] markers."""
        html = "<div class='comment'>[removed]</div>"
        url = "https://reddit.com/r/test/comments/abc123"

        result = detect_deletion(html_content=html, url=url)

        assert result is not None
        assert result["platform"] == "reddit"


class TestFlagAsDeleted:
    """Test the flag_as_deleted function."""

    def test_flag_metadata_as_deleted(self):
        """Verify that metadata is properly flagged with deletion info."""
        metadata = Metadata()
        deletion_info = {
            "is_deleted": True,
            "indicator": "This Tweet is unavailable",
            "source": "html_content",
            "platform": "twitter"
        }

        flag_as_deleted(metadata, deletion_info)

        assert metadata.get("deletion_detected") is True
        assert metadata.get("deletion_indicator") == "This Tweet is unavailable"
        assert metadata.get("deletion_source") == "html_content"
        assert metadata.get("deletion_platform") == "twitter"
        assert metadata.status == "deleted_or_unavailable"

    def test_metadata_contains_deletion_context(self):
        """Verify investigators have full context about the deletion."""
        metadata = Metadata()
        deletion_info = {
            "is_deleted": True,
            "indicator": "Video has been removed by the uploader",
            "source": "error_message",
            "platform": "youtube"
        }

        flag_as_deleted(metadata, deletion_info)

        # This metadata can now be stored so investigators know:
        # - The content existed but was deleted
        # - Exactly what message indicated deletion
        # - Which platform it was from
        # - When it was checked (via _processed_at)
        assert "deletion_indicator" in metadata.metadata
        assert "uploader" in metadata.get("deletion_indicator")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
