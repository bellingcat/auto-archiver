"""
Tests for the MuteFormatter module
"""

import pytest
from auto_archiver.core.metadata import Metadata


@pytest.fixture
def mute_formatter(setup_module):
    return setup_module("mute_formatter")


class TestMuteFormatter:
    """Test the MuteFormatter functionality."""

    def test_format_returns_none(self, mute_formatter, make_item):
        """Test that format always returns None (mutes output)."""
        item = make_item("https://example.com/test")
        item.set("title", "Test Title")

        result = mute_formatter.format(item)

        assert result is None

    def test_format_with_empty_metadata(self, mute_formatter):
        """Test format with empty metadata."""
        item = Metadata().set_url("https://example.com/empty")

        result = mute_formatter.format(item)

        assert result is None

    def test_format_with_media(self, mute_formatter, make_item):
        """Test that format still returns None even with media attached."""
        from auto_archiver.core.media import Media

        item = make_item("https://example.com/with-media")
        item.add_media(Media(filename="test.mp4"))

        result = mute_formatter.format(item)

        assert result is None
