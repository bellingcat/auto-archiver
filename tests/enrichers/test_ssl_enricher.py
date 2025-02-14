import ssl
from unittest.mock import patch, mock_open

import pytest

from auto_archiver.core import Metadata, Media


@pytest.fixture
def enricher(setup_module):
    configs: dict = {
        "skip_when_nothing_archived": "True",
    }
    return setup_module("ssl_enricher", configs)


@pytest.fixture
def metadata():
    m = Metadata()
    m.set_url("https://example.com")
    m.add_media(Media("tests/data/testfile_1.txt"))
    m.add_media(Media("tests/data/testfile_2.txt"))
    return m


def test_http_raises(metadata, enricher):
    metadata.set_url("http://example.com")
    with pytest.raises(AssertionError) as exc_info:
        enricher.enrich(metadata)
    assert "Invalid URL scheme" in str(exc_info.value)


def test_empty_metadata(metadata, enricher):
    metadata.media = []
    assert enricher.enrich(metadata) is None


def test_ssl_enrich(metadata, enricher):
    with patch("ssl.get_server_certificate", return_value="TEST_CERT"), \
         patch("builtins.open", mock_open()) as mock_file:
        media_len_before = len(metadata.media)
        enricher.enrich(metadata)

        ssl.get_server_certificate.assert_called_once_with(("example.com", 443))
        mock_file.assert_called_once_with(f"{enricher.tmp_dir}/example-com.pem", "w")
        mock_file().write.assert_called_once_with("TEST_CERT")
        assert len(metadata.media) == media_len_before + 1
        # Ensure the certificate is added to metadata
        assert any(media.filename.endswith("example-com.pem") for media in metadata.media)


def test_ssl_error_handling(enricher, metadata):
    with patch("ssl.get_server_certificate", side_effect=ssl.SSLError("SSL error")):
        with pytest.raises(ssl.SSLError, match="SSL error"):
            enricher.enrich(metadata)

