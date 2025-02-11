import datetime
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from auto_archiver.core import Metadata, Media
from auto_archiver.modules.meta_enricher import MetaEnricher


@pytest.fixture
def mock_metadata():
    """Creates a mock Metadata object."""
    mock: Metadata = MagicMock(spec=Metadata)
    mock.get_url.return_value = "https://example.com"
    mock.is_empty.return_value = False  # Default to not empty
    mock.get_all_media.return_value = []
    return mock

@pytest.fixture
def mock_media():
    """Creates a mock Media object."""
    mock: Media = MagicMock(spec=Media)
    mock.filename = "mock_file.txt"
    return mock

@pytest.fixture
def metadata():
    m = Metadata()
    m.set_url("https://example.com")
    m.set_title("Test Title")
    m.set_content("Test Content")
    return m


@pytest.fixture(autouse=True)
def meta_enricher(setup_module):
    return setup_module(MetaEnricher, {})


def test_enrich_skips_empty_metadata(meta_enricher, mock_metadata):
    """Test that enrich() does nothing when Metadata is empty."""
    mock_metadata.is_empty.return_value = True
    meta_enricher.enrich(mock_metadata)
    mock_metadata.get_url.assert_called_once()


def test_enrich_file_sizes(meta_enricher, metadata, tmp_path):
    """Test that enrich_file_sizes() calculates and sets file sizes correctly."""
    file1 = tmp_path / "testfile_1.txt"
    file2 = tmp_path / "testfile_2.txt"
    file1.write_text("A" * 1000)
    file2.write_text("B" * 2000)
    metadata.add_media(Media(str(file1)))
    metadata.add_media(Media(str(file2)))

    meta_enricher.enrich_file_sizes(metadata)

    # Verify individual media file sizes
    media1 = metadata.get_all_media()[0]
    media2 = metadata.get_all_media()[1]

    assert media1.get("bytes") == 1000
    assert media1.get("size") == "1000.0 bytes"
    assert media2.get("bytes") == 2000
    assert media2.get("size") == "2.0 KB"

    assert metadata.get("total_bytes") == 3000
    assert metadata.get("total_size") == "2.9 KB"

@pytest.mark.parametrize(
    "size, expected",
    [
        (500, "500.0 bytes"),
        (1024, "1.0 KB"),
        (2048, "2.0 KB"),
        (1048576, "1.0 MB"),
        (1073741824, "1.0 GB"),
    ],
)
def test_human_readable_bytes(size, expected):
    """Test that human_readable_bytes() converts sizes correctly."""
    enricher = MetaEnricher()
    assert enricher.human_readable_bytes(size) == expected

def test_enrich_file_sizes_no_media(meta_enricher, metadata):
    """Test that enrich_file_sizes() handles empty media list gracefully."""
    meta_enricher.enrich_file_sizes(metadata)
    assert metadata.get("total_bytes") == 0
    assert metadata.get("total_size") == "0.0 bytes"


def test_enrich_archive_duration(meta_enricher, metadata):
    # Set fixed "processed at" time in the past
    processed_at = datetime.now(timezone.utc) - timedelta(minutes=10, seconds=30)
    metadata.set("_processed_at", processed_at)
    # patch datetime
    with patch("datetime.datetime") as mock_datetime:
        mock_now = datetime.now(timezone.utc)
        mock_datetime.now.return_value = mock_now
        meta_enricher.enrich_archive_duration(metadata)

    assert metadata.get("archive_duration_seconds") == 630