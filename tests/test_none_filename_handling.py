"""
Tests for handling Media objects with None filename.

When download_from_url fails, it returns None. Various enrichers and
the metadata deduplication logic must gracefully handle Media objects
where filename is None, rather than crashing with TypeError.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from auto_archiver.core.metadata import Metadata, Media
from auto_archiver.modules.hash_enricher import HashEnricher
from auto_archiver.modules.meta_enricher import MetaEnricher


# ── HashEnricher ──────────────────────────────────────────────────────


class TestHashEnricherNoneFilename:
    """hash_enricher should skip media with None filename without crashing."""

    @pytest.fixture(autouse=True)
    def setup(self, setup_module):
        self.enricher = setup_module(HashEnricher, {"algorithm": "SHA-256", "chunksize": 100})

    def test_skips_none_filename(self):
        m = Metadata().set_url("https://example.com")
        media = Media(filename=None)
        media.set("src", "https://example.com/video.mp4")
        m.add_media(media)

        # Should not raise
        self.enricher.enrich(m)
        # No hash should be set
        assert m.media[0].get("hash") is None

    def test_hashes_valid_skips_none(self, tmp_path):
        """Mix of valid and None-filename media: only valid ones get hashed."""
        valid_file = tmp_path / "test.txt"
        valid_file.write_text("hello world")

        m = Metadata().set_url("https://example.com")
        m.add_media(Media(filename=str(valid_file)))
        m.add_media(Media(filename=None))

        self.enricher.enrich(m)

        assert m.media[0].get("hash") is not None
        assert m.media[1].get("hash") is None

    def test_all_none_filenames(self):
        """All media have None filename – enricher should not crash."""
        m = Metadata().set_url("https://example.com")
        m.add_media(Media(filename=None))
        m.add_media(Media(filename=None))

        self.enricher.enrich(m)

        assert len(m.media) == 2
        for media in m.media:
            assert media.get("hash") is None


# ── MetaEnricher ──────────────────────────────────────────────────────


class TestMetaEnricherNoneFilename:
    """meta_enricher should skip media with None filename without crashing."""

    @pytest.fixture(autouse=True)
    def setup(self, setup_module):
        self.enricher = setup_module(MetaEnricher, {})

    def test_skips_none_filename(self):
        m = Metadata().set_url("https://example.com")
        m.set("_processed_at", datetime.now(timezone.utc))
        media = Media(filename=None)
        media.set("src", "https://example.com/video.mp4")
        m.add_media(media)

        # Should not raise
        self.enricher.enrich(m)
        assert m.get("total_bytes") == 0

    def test_sizes_valid_skips_none(self, tmp_path):
        """Mix of valid and None-filename media: only valid ones get sized."""
        valid_file = tmp_path / "test.txt"
        valid_file.write_text("A" * 500)

        m = Metadata().set_url("https://example.com")
        m.set("_processed_at", datetime.now(timezone.utc))
        m.add_media(Media(filename=str(valid_file)))
        m.add_media(Media(filename=None))

        self.enricher.enrich(m)

        assert m.media[0].get("bytes") == 500
        assert m.media[1].get("bytes") is None
        assert m.get("total_bytes") == 500


# ── Metadata.remove_duplicate_media_by_hash ───────────────────────────


class TestRemoveDuplicateMediaNoneFilename:
    """remove_duplicate_media_by_hash should keep media with None filename."""

    def test_none_filename_kept(self):
        m = Metadata().set_url("https://example.com")
        none_media = Media(filename=None)
        none_media.set("src", "https://example.com/video.mp4")
        m.add_media(none_media)

        m.remove_duplicate_media_by_hash()

        assert len(m.media) == 1
        assert m.media[0].filename is None

    def test_none_and_valid_mixed(self, tmp_path):
        """None-filename media is kept alongside valid-filename media."""
        valid_file = tmp_path / "test.txt"
        valid_file.write_text("content")

        m = Metadata().set_url("https://example.com")
        m.add_media(Media(filename=str(valid_file)))
        none_media = Media(filename=None)
        none_media.set("src", "https://example.com/video.mp4")
        m.add_media(none_media)

        m.remove_duplicate_media_by_hash()

        assert len(m.media) == 2

    def test_multiple_none_filename_all_kept(self):
        """Multiple None-filename media are all kept (can't deduplicate without file)."""
        m = Metadata().set_url("https://example.com")
        m.add_media(Media(filename=None))
        m.add_media(Media(filename=None))

        m.remove_duplicate_media_by_hash()

        assert len(m.media) == 2


# ── Twitter dropin create_metadata ────────────────────────────────────


class TestTwitterDropinNoneFilename:
    """Twitter dropin should skip media when download_from_url returns None."""

    @pytest.fixture
    def twitter_dropin(self):
        from auto_archiver.modules.generic_extractor.twitter import Twitter

        return Twitter()

    def test_create_metadata_skips_failed_photo_download(self, twitter_dropin):
        """When download_from_url returns None for a photo, it's not added to media."""
        tweet = {
            "user": {"name": "Test User"},
            "created_at": "Sun Feb 08 18:45:00 +0000 2026",
            "full_text": "Test tweet with photo",
            "entities": {
                "media": [
                    {"type": "photo", "media_url_https": "https://pbs.twimg.com/media/test.jpg"},
                ]
            },
        }

        mock_archiver = MagicMock()
        mock_archiver.download_from_url.return_value = None  # simulate failed download

        result = twitter_dropin.create_metadata(tweet, None, mock_archiver, "https://x.com/test/status/123")

        # The result should have no media since the download failed
        assert len(result.media) == 0

    def test_create_metadata_skips_failed_video_download(self, twitter_dropin):
        """When download_from_url returns None for a video, it's not added to media."""
        tweet = {
            "user": {"name": "Test User"},
            "created_at": "Sun Feb 08 18:45:00 +0000 2026",
            "full_text": "Test tweet with video",
            "entities": {
                "media": [
                    {
                        "type": "video",
                        "video_info": {
                            "variants": [
                                {
                                    "url": "https://video.twimg.com/vid/1280x720/test.mp4",
                                    "content_type": "video/mp4",
                                },
                            ]
                        },
                    },
                ]
            },
        }

        mock_archiver = MagicMock()
        mock_archiver.download_from_url.return_value = None

        result = twitter_dropin.create_metadata(tweet, None, mock_archiver, "https://x.com/test/status/123")

        assert len(result.media) == 0

    def test_create_metadata_keeps_successful_download(self, twitter_dropin, tmp_path):
        """When download_from_url succeeds, media is added."""
        tweet = {
            "user": {"name": "Test User"},
            "created_at": "Sun Feb 08 18:45:00 +0000 2026",
            "full_text": "Test tweet with photo",
            "entities": {
                "media": [
                    {"type": "photo", "media_url_https": "https://pbs.twimg.com/media/test.jpg"},
                ]
            },
        }

        test_file = tmp_path / "test.jpg"
        test_file.write_text("fake image data")

        mock_archiver = MagicMock()
        mock_archiver.download_from_url.return_value = str(test_file)

        result = twitter_dropin.create_metadata(tweet, None, mock_archiver, "https://x.com/test/status/123")

        assert len(result.media) == 1
        assert result.media[0].filename == str(test_file)

    def test_create_metadata_mixed_downloads(self, twitter_dropin, tmp_path):
        """One download succeeds, one fails – only successful one is kept."""
        tweet = {
            "user": {"name": "Test User"},
            "created_at": "Sun Feb 08 18:45:00 +0000 2026",
            "full_text": "Test tweet with two photos",
            "entities": {
                "media": [
                    {"type": "photo", "media_url_https": "https://pbs.twimg.com/media/test1.jpg"},
                    {"type": "photo", "media_url_https": "https://pbs.twimg.com/media/test2.jpg"},
                ]
            },
        }

        test_file = tmp_path / "test1.jpg"
        test_file.write_text("fake image data")

        mock_archiver = MagicMock()
        # First call succeeds, second fails
        mock_archiver.download_from_url.side_effect = [str(test_file), None]

        result = twitter_dropin.create_metadata(tweet, None, mock_archiver, "https://x.com/test/status/123")

        assert len(result.media) == 1
        assert result.media[0].filename == str(test_file)
