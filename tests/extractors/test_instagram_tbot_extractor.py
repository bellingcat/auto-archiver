import os
import pickle
from typing import Type
from unittest.mock import patch, MagicMock

import pytest

from auto_archiver.core.extractor import Extractor
from auto_archiver.modules.instagram_tbot_extractor import InstagramTbotExtractor


TESTFILES = os.path.join(os.path.dirname(__file__), "testfiles")


@pytest.fixture
def test_session_file(tmpdir):
    """Fixture to create a test session file."""
    session_file = os.path.join(tmpdir, "test_session.session")
    with open(session_file, "w") as f:
        f.write("mock_session_data")
    return session_file.replace(".session", "")


@pytest.mark.incremental
class TestInstagramTbotExtractor(object):
    """
    Test suite for InstagramTbotExtractor.
    """

    extractor_module = "instagram_tbot_extractor"
    extractor: InstagramTbotExtractor
    config = {
        "api_id": 12345,
        "api_hash": "test_api_hash",
        # "session_file"
    }

    @pytest.fixture(autouse=True)
    def setup_extractor(self, setup_module):
        assert self.extractor_module is not None, "self.extractor_module must be set on the subclass"
        assert self.config is not None, "self.config must be a dict set on the subclass"
        extractor: Type[Extractor] = setup_module(self.extractor_module, self.config)
        return extractor

    @pytest.fixture
    def mock_telegram_client(self):
        """Fixture to mock TelegramClient interactions."""
        with patch("auto_archiver.modules.instagram_tbot_extractor._initialize_telegram_client") as mock_client:
            instance = MagicMock()
            mock_client.return_value = instance
            yield instance


    # @pytest.fixture
    # def mock_session_file(self, temp_session_file):
    #     """Patch the extractor’s session file setup to use a temporary path."""
    #     with patch.object(InstagramTbotExtractor, "session_file", temp_session_file):
    #         with patch.object(InstagramTbotExtractor, "_prepare_session_file", return_value=None):
    #             yield  # Mocks are applied for the duration of the test

    @pytest.fixture
    def metadata_sample(self):
        """Loads a Metadata object from a pickle file."""
        with open(os.path.join(TESTFILES, "metadata_item.pkl"), "rb") as f:
            return pickle.load(f)


    @pytest.mark.download
    @pytest.mark.parametrize("url, expected_status, bot_responses", [
        ("https://www.instagram.com/p/C4QgLbrIKXG", "insta-via-bot: success", [MagicMock(id=101, media=None, message="Are you new to Bellingcat? - The way we share our investigations is different. 💭\nWe want you to read our story but also learn ou")]),
        ("https://www.instagram.com/reel/DEVLK8qoIbg/", "insta-via-bot: success", [MagicMock(id=101, media=None, message="Our volunteer community is at the centre of many incredible Bellingcat investigations and tools. Stephanie Ladel is one such vol")]),
        # todo tbot not working for stories :(
        ("https://www.instagram.com/stories/bellingcatofficial/3556336382743057476/", False, [MagicMock(id=101, media=None, message="Media not found or unavailable")]),
        ("https://www.youtube.com/watch?v=ymCMy8OffHM", False, []),
        ("https://www.instagram.com/p/INVALID", False, [MagicMock(id=101, media=None, message="You must enter a URL to a post")]),
    ])
    def test_download(self, url, expected_status, bot_responses, metadata_sample):
        """Test the `download()` method with various Instagram URLs."""
        metadata_sample.set_url(url)
        self.extractor.initialise()
        result = self.extractor.download(metadata_sample)
        if expected_status:
            assert result.is_success()
            assert result.status == expected_status
            assert result.metadata.get("title") in [msg.message[:128] for msg in bot_responses if msg.message]
        else:
            assert result is False
        # self.extractor.cleanup()

    # @patch.object(InstagramTbotExtractor, '_send_url_to_bot')
    # @patch.object(InstagramTbotExtractor, '_process_messages')
    # def test_download_invalid_link_returns_false(
    #     self, mock_process, mock_send, extractor, metadata_instagram
    # ):
    #     # Setup Mocks
    #     # _send_url_to_bot -> simulate it returns (chat=MagicMock, since_id=100)
    #     mock_chat = MagicMock()
    #     mock_send.return_value = (mock_chat, 100)
    #     # _process_messages -> simulate it returns the text "You must enter a URL to a post"
    #     mock_process.return_value = "You must enter a URL to a post"
    #     result = extractor.download(metadata_instagram)
    #     assert result is False, "Should return False if message includes 'You must enter a URL to a post'"




        # Test story
# Test expired story
# Test requires login/ access (?)
# Test post
# Test multiple images?