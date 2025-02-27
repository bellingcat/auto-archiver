import pytest

from auto_archiver.core import Metadata
from auto_archiver.modules.vk_extractor import VkExtractor


@pytest.fixture
def mock_vk_scraper(mocker):
    """Fixture to mock VkScraper."""
    return mocker.patch("auto_archiver.modules.vk_extractor.vk_extractor.VkScraper")

@pytest.fixture
def vk_extractor(setup_module, mock_vk_scraper) -> VkExtractor:
    """Fixture to initialize VkExtractor with mocked VkScraper."""
    extractor_module = "vk_extractor"
    configs = {
        "username": "name",
        "password": "password123",
        "session_file": "secrets/vk_config.v2.json",
    }
    vk = setup_module(extractor_module, configs)
    vk.vks = mock_vk_scraper.return_value
    return vk


def test_netloc(vk_extractor, metadata):
    # metadata url set as: "https://example.com/"
    assert vk_extractor.download(metadata) is False


def test_vk_url_but_scrape_returns_empty(vk_extractor, metadata):
    metadata.set_url("https://vk.com/valid-wall")
    vk_extractor.vks.scrape.return_value = []
    assert vk_extractor.download(metadata) is False
    assert metadata.netloc == "vk.com"
    vk_extractor.vks.scrape.assert_called_once_with(metadata.get_url())


def test_successful_scrape_and_download(vk_extractor, metadata, mocker):
    mock_scrapes = [
        {"text": "Post Title", "datetime": "2023-01-01T00:00:00", "id": 1},
        {"text": "Another Post", "datetime": "2023-01-02T00:00:00", "id": 2}
    ]
    mock_filenames = ["image1.jpg", "image2.png"]
    vk_extractor.vks.scrape.return_value = mock_scrapes
    vk_extractor.vks.download_media.return_value = mock_filenames
    metadata.set_url("https://vk.com/valid-wall")
    result = vk_extractor.download(metadata)
    # Test metadata
    assert result.is_success()
    assert result.status == "vk: success"
    assert result.get_title() == "Post Title"
    assert result.get_timestamp() == "2023-01-01T00:00:00+00:00"
    assert "Another Post" in result.metadata["content"]
    # Test Media objects
    assert len(result.media) == 2
    assert result.media[0].filename == "image1.jpg"
    assert result.media[1].filename == "image2.png"
    vk_extractor.vks.download_media.assert_called_once_with(
        mock_scrapes, vk_extractor.tmp_dir
    )


def test_adds_first_title_and_timestamp(vk_extractor):
    metadata = Metadata().set_url("https://vk.com/no-metadata")
    metadata.set_url("https://vk.com/no-metadata")
    mock_scrapes = [{"text": "value", "datetime": "2023-01-01T00:00:00"},
                    {"text": "value2", "datetime": "2023-01-02T00:00:00"}]
    vk_extractor.vks.scrape.return_value = mock_scrapes
    vk_extractor.vks.download_media.return_value = []
    result = vk_extractor.download(metadata)

    assert result.get_title() == "value"
    # formatted timestamp
    assert result.get_timestamp() == "2023-01-01T00:00:00+00:00"
    assert result.is_success()