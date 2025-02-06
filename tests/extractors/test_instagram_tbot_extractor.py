import os
import pickle
from typing import Type
from unittest.mock import patch, MagicMock

import pytest

from auto_archiver.core import Metadata
from auto_archiver.core.extractor import Extractor
from auto_archiver.modules.instagram_tbot_extractor import InstagramTbotExtractor
from tests.extractors.test_extractor_base import TestExtractorBase

TESTFILES = os.path.join(os.path.dirname(__file__), "testfiles")


@pytest.fixture
def session_file(tmpdir):
    """Fixture to create a test session file."""
    session_file = os.path.join(tmpdir, "test_session.session")
    with open(session_file, "w") as f:
        f.write("mock_session_data")
    return session_file.replace(".session", "")


@pytest.fixture(autouse=True)
def patch_extractor_methods(request, setup_module):
    with patch.object(InstagramTbotExtractor, '_prepare_session_file', return_value=None), \
            patch.object(InstagramTbotExtractor, '_initialize_telegram_client', return_value=None):
        if hasattr(request, 'cls') and hasattr(request.cls, 'config'):
            request.cls.extractor = setup_module("instagram_tbot_extractor", request.cls.config)

        yield

@pytest.fixture
def metadata_sample():
    m = Metadata()
    m.set_title("Test Title")
    m.set_timestamp("2021-01-01T00:00:00Z")
    m.set_url("https://www.instagram.com/p/1234567890")
    return m


class TestInstagramTbotExtractor:

    extractor_module = "instagram_tbot_extractor"
    extractor: InstagramTbotExtractor
    config = {
        "api_id": 12345,
        "api_hash": "test_api_hash",
        "session_file": "test_session",
    }

    @pytest.fixture
    def mock_telegram_client(self):
        """Fixture to mock TelegramClient interactions."""
        with patch("auto_archiver.modules.instagram_tbot_extractor._initialize_telegram_client") as mock_client:
            instance = MagicMock()
            mock_client.return_value = instance
            yield instance

    def test_extractor_is_initialized(self):
        assert self.extractor is not None


    @patch("time.sleep")
    @pytest.mark.parametrize("url, expected_status, bot_responses", [
        ("https://www.instagram.com/p/C4QgLbrIKXG", "insta-via-bot: success", [MagicMock(id=101, media=None, message="Are you new to Bellingcat? - The way we share our investigations is different. 💭\nWe want you to read our story but also learn ou")]),
        ("https://www.instagram.com/reel/DEVLK8qoIbg/", "insta-via-bot: success", [MagicMock(id=101, media=None, message="Our volunteer community is at the centre of many incredible Bellingcat investigations and tools. Stephanie Ladel is one such vol")]),
        # todo tbot not working for stories :(
        ("https://www.instagram.com/stories/bellingcatofficial/3556336382743057476/", False, [MagicMock(id=101, media=None, message="Media not found or unavailable")]),
        ("https://www.youtube.com/watch?v=ymCMy8OffHM", False, []),
        ("https://www.instagram.com/p/INVALID", False, [MagicMock(id=101, media=None, message="You must enter a URL to a post")]),
    ])
    def test_download(self, mock_sleep, url, expected_status, bot_responses, metadata_sample):
        """Test the `download()` method with various Instagram URLs."""
        metadata_sample.set_url(url)
        self.extractor.client = MagicMock()
        result = self.extractor.download(metadata_sample)
        pass
        # TODO fully mock or use as authenticated test
        # if expected_status:
        #     assert result.is_success()
        #     assert result.status == expected_status
        #     assert result.metadata.get("title") in [msg.message[:128] for msg in bot_responses if msg.message]
        # else:
        #     assert result is False




        # Test story
# Test expired story
# Test requires login/ access (?)
# Test post
# Test multiple images?