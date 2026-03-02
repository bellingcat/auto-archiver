"""
Tests for the Media class from auto_archiver.core.media
"""

import pytest
from unittest.mock import Mock, patch
from auto_archiver.core.media import Media


class TestMediaBasics:
    """Test basic Media properties and methods."""

    def test_media_creation_with_filename(self):
        media = Media(filename="test.mp4")
        assert media.filename == "test.mp4"
        assert media.urls == []
        assert media.properties == {}

    def test_media_key_property(self):
        media = Media(filename="test.mp4", _key="my_key")
        assert media.key == "my_key"

    def test_media_set_get_properties(self):
        media = Media(filename="test.mp4")
        result = media.set("author", "John Doe")
        assert result is media  # returns self for chaining
        assert media.get("author") == "John Doe"
        assert media.get("nonexistent") is None
        assert media.get("nonexistent", "default") == "default"

    def test_media_add_url(self):
        media = Media(filename="test.mp4")
        media.add_url("https://example.com/test.mp4")
        assert "https://example.com/test.mp4" in media.urls
        media.add_url("https://cdn.example.com/test.mp4")
        assert len(media.urls) == 2


class TestMediaMimetype:
    """Test mimetype detection and handling."""

    @pytest.mark.parametrize(
        "filename,expected_mimetype",
        [
            ("video.mp4", "video/mp4"),
            ("image.jpg", "image/jpeg"),
            ("image.png", "image/png"),
            ("audio.mp3", "audio/mpeg"),
            ("document.pdf", "application/pdf"),
            ("text.txt", "text/plain"),
        ],
    )
    def test_mimetype_detection(self, filename, expected_mimetype):
        media = Media(filename=filename)
        assert media.mimetype == expected_mimetype

    def test_mimetype_setter(self):
        media = Media(filename="file.unknown")
        media.mimetype = "custom/type"
        assert media.mimetype == "custom/type"

    def test_mimetype_empty_filename(self):
        media = Media(filename="")
        assert media.mimetype == ""


class TestMediaTypeChecks:
    """Test media type checking methods."""

    @pytest.mark.parametrize(
        "filename,is_video,is_audio,is_image",
        [
            ("video.mp4", True, False, False),
            ("video.avi", True, False, False),
            ("audio.mp3", False, True, False),
            ("audio.wav", False, True, False),
            ("image.jpg", False, False, True),
            ("image.png", False, False, True),
            ("document.pdf", False, False, False),
        ],
    )
    def test_type_checks(self, filename, is_video, is_audio, is_image):
        media = Media(filename=filename)
        assert media.is_video() == is_video
        assert media.is_audio() == is_audio
        assert media.is_image() == is_image


class TestMediaStore:
    """Test media storage functionality."""

    def test_store_with_no_storages(self, caplog):
        media = Media(filename="test.mp4")
        metadata = Mock()
        media.store(metadata, storages=[])
        assert "No storages found" in caplog.text

    def test_store_with_storage(self):
        media = Media(filename="test.mp4")
        metadata = Mock()
        mock_storage = Mock()
        media.store(metadata, url="https://example.com", storages=[mock_storage])
        mock_storage.store.assert_called_once()


class TestMediaInnerMedia:
    """Test nested media retrieval."""

    def test_all_inner_media_no_nested(self):
        media = Media(filename="test.mp4")
        inner = list(media.all_inner_media(include_self=False))
        assert len(inner) == 0

        inner_with_self = list(media.all_inner_media(include_self=True))
        assert len(inner_with_self) == 1
        assert inner_with_self[0] is media

    def test_all_inner_media_with_nested(self):
        parent = Media(filename="parent.mp4")
        child = Media(filename="child.jpg")
        grandchild = Media(filename="grandchild.png")

        child.set("thumbnail", grandchild)
        parent.set("preview", child)

        inner = list(parent.all_inner_media(include_self=False))
        assert len(inner) == 2
        assert child in inner
        assert grandchild in inner

    def test_all_inner_media_with_list_property(self):
        parent = Media(filename="parent.mp4")
        child1 = Media(filename="frame1.jpg")
        child2 = Media(filename="frame2.jpg")

        parent.set("frames", [child1, child2])

        inner = list(parent.all_inner_media(include_self=False))
        assert len(inner) == 2
        assert child1 in inner
        assert child2 in inner


class TestMediaIsStored:
    """Test the is_stored method."""

    def test_is_stored_no_urls(self):
        media = Media(filename="test.mp4")
        storage = Mock()
        storage.config = {"steps": {"storages": ["s3", "local"]}}
        assert media.is_stored(storage) is False

    def test_is_stored_partial_urls(self):
        media = Media(filename="test.mp4")
        media.add_url("https://s3.example.com/test.mp4")
        storage = Mock()
        storage.config = {"steps": {"storages": ["s3", "local"]}}
        assert media.is_stored(storage) is False

    def test_is_stored_full_urls(self):
        media = Media(filename="test.mp4")
        media.add_url("https://s3.example.com/test.mp4")
        media.add_url("file:///local/test.mp4")
        storage = Mock()
        storage.config = {"steps": {"storages": ["s3", "local"]}}
        assert media.is_stored(storage) is True


class TestMediaValidVideo:
    """Test video validation functionality."""

    def test_is_valid_video_with_valid_probe(self):
        media = Media(filename="test.mp4")

        mock_streams = {"streams": [{"duration_ts": 1000}]}

        with patch("ffmpeg.probe", return_value=mock_streams):
            assert media.is_valid_video() is True

    def test_is_valid_video_with_no_duration(self):
        media = Media(filename="test.mp4")

        mock_streams = {"streams": [{"duration_ts": 0}]}

        with patch("ffmpeg.probe", return_value=mock_streams):
            assert media.is_valid_video() is False

    def test_is_valid_video_with_ffmpeg_error(self):
        media = Media(filename="test.mp4")

        with patch("ffmpeg.probe", side_effect=Exception("ffmpeg error")):
            with patch("os.path.getsize", return_value=100):
                # Falls back to file size check, small file
                assert media.is_valid_video() is False

            with patch("os.path.getsize", return_value=30000):
                # Falls back to file size check, larger file
                assert media.is_valid_video() is True
