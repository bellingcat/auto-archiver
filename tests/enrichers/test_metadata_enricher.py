from unittest.mock import MagicMock, patch, Mock

import pytest

from auto_archiver.core import Metadata, Media


@pytest.fixture
def mock_media():
    """Creates a mock Media object."""
    mock: Media = MagicMock(spec=Media)
    mock.filename = "mock_file.txt"
    return mock


@pytest.fixture
def enricher(setup_module):
    return setup_module("metadata_enricher", {})


@pytest.mark.parametrize(
    "output,expected",
    [
        ("Key1: Value1\nKey2: Value2", {"Key1": "Value1", "Key2": "Value2"}),
        ("InvalidLine", {}),
        ("", {}),
    ],
)
@patch("subprocess.run")
def test_get_metadata(mock_run, enricher, output, expected):
    mock_run.return_value.stdout = output
    mock_run.return_value.stderr = ""
    mock_run.return_value.returncode = 0

    result = enricher.get_metadata("test.jpg")
    assert result == expected
    mock_run.assert_called_once_with(
        ["exiftool", "test.jpg"], capture_output=True, text=True
    )


@patch("subprocess.run")
def test_get_metadata_exiftool_not_found(mock_run, enricher):
    mock_run.side_effect = FileNotFoundError
    result = enricher.get_metadata("test.jpg")
    assert result == {}


def test_enrich_sets_metadata(enricher):
    media1 = Mock(filename="img1.jpg")
    media2 = Mock(filename="img2.jpg")
    metadata = Mock()
    metadata.media = [media1, media2]
    enricher.get_metadata = lambda f: {"key": "value"} if f == "img1.jpg" else {}

    enricher.enrich(metadata)

    media1.set.assert_called_once_with("metadata", {"key": "value"})
    media2.set.assert_not_called()
    assert metadata.media == [media1, media2]


def test_enrich_empty_media(enricher):
    metadata = Mock()
    metadata.media = []
    # Should not raise errors
    enricher.enrich(metadata)


@patch("loguru.logger.error")
@patch("subprocess.run")
def test_get_metadata_error_handling(mock_run, mock_logger_error, enricher):
    mock_run.side_effect = Exception("Test error")
    result = enricher.get_metadata("test.jpg")
    assert result == {}
    mock_logger_error.assert_called_once()
