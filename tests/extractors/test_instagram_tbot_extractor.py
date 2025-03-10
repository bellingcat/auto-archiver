import os

import pytest

from auto_archiver.core import Metadata
from auto_archiver.modules.instagram_tbot_extractor import InstagramTbotExtractor
from tests.extractors.test_extractor_base import TestExtractorBase


@pytest.fixture
def patch_extractor_methods(request, setup_module, mocker):
    mocker.patch.object(InstagramTbotExtractor, "_prepare_session_file", return_value=None)
    mocker.patch.object(InstagramTbotExtractor, "_initialize_telegram_client", return_value=None)
    yield


@pytest.fixture
def metadata_sample():
    m = Metadata()
    m.set_title("Test Title")
    m.set_timestamp("2021-01-01T00:00:00")
    m.set_url("https://www.instagram.com/p/1234567890")
    return m


@pytest.fixture
def mock_telegram_client(mocker):
    """Fixture to mock TelegramClient interactions."""
    mock_client = mocker.patch("auto_archiver.modules.instagram_tbot_extractor.client")
    instance = mocker.MagicMock()
    mock_client.return_value = instance
    return instance


@pytest.fixture
def extractor(setup_module, patch_extractor_methods, mocker):
    extractor_module = "instagram_tbot_extractor"
    config = {"api_id": 12345, "api_hash": "test_api_hash", "session_file": "test_session", "timeout": 4}
    extractor = setup_module(extractor_module, config)
    extractor.client = mocker.MagicMock()
    extractor.session_file = "test_session"
    return extractor


def test_non_instagram_url(extractor, metadata_sample):
    metadata_sample.set_url("https://www.youtube.com")
    assert extractor.download(metadata_sample) is False


def test_download_success(extractor, metadata_sample, mocker):
    mocker.patch.object(extractor, "_send_url_to_bot", return_value=(mocker.MagicMock(), 101))
    mocker.patch.object(extractor, "_process_messages", return_value="Sample Instagram post caption")
    result = extractor.download(metadata_sample)
    assert result.is_success()
    assert result.status == "insta-via-bot: success"
    assert result.metadata.get("title") == "Sample Instagram post caption"


def test_download_invalid(extractor, metadata_sample, mocker):
    mocker.patch.object(extractor, "_send_url_to_bot", return_value=(mocker.MagicMock(), 101))
    mocker.patch.object(extractor, "_process_messages", return_value="You must enter a URL to a post")
    assert extractor.download(metadata_sample) is False


@pytest.mark.skip(reason="Requires authentication.")
class TestInstagramTbotExtractorReal(TestExtractorBase):
    # To run these tests set the TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables, and ensure the session file exists.
    # Note these are true at this point in time, but changes to source media could be reason for failure.
    extractor_module = "instagram_tbot_extractor"
    extractor: InstagramTbotExtractor
    config = {
        "api_id": os.environ.get("TELEGRAM_API_ID"),
        "api_hash": os.environ.get("TELEGRAM_API_HASH"),
        "session_file": "secrets/anon-insta",
    }

    @pytest.mark.parametrize(
        "url, expected_status, message, len_media",
        [
            (
                "https://www.instagram.com/p/C4QgLbrIKXG",
                "insta-via-bot: success",
                "Are you new to Bellingcat? - The way we share our investigations is different. 💭\nWe want you to read our story but also learn ou",
                6,
            ),
            (
                "https://www.instagram.com/reel/DEVLK8qoIbg/",
                "insta-via-bot: success",
                "Our volunteer community is at the centre of many incredible Bellingcat investigations and tools. Stephanie Ladel is one such vol",
                3,
            ),
            # instagram tbot not working (potentially intermittently?) for stories - replace with a live story to retest
            # ("https://www.instagram.com/stories/bellingcatofficial/3556336382743057476/", False, "Media not found or unavailable"),
            # Seems to be working intermittently for highlights
            # ("https://www.instagram.com/stories/highlights/17868810693068139/", "insta-via-bot: success", None, 50),
            # Marking invalid url as success
            ("https://www.instagram.com/p/INVALID", "insta-via-bot: success", "Media not found or unavailable", 0),
            ("https://www.youtube.com/watch?v=ymCMy8OffHM", False, None, 0),
        ],
    )
    def test_download(self, url, expected_status, message, len_media, metadata_sample):
        """Test the `download()` method with various Instagram URLs."""
        metadata_sample.set_url(url)

        result = self.extractor.download(metadata_sample)
        if expected_status:
            assert result.is_success()
            assert result.status == expected_status
            assert result.metadata.get("title") == message
            assert len(result.media) == len_media
        else:
            assert result is False
