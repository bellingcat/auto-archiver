import shutil
import sys
import pytest
from unittest.mock import MagicMock, patch
from auto_archiver.core import Metadata, Media
from auto_archiver.modules.s3_storage import S3Storage

from auto_archiver.modules.whisper_enricher import WhisperEnricher


@pytest.fixture
def enricher():
    """Fixture with mocked S3 and API dependencies"""
    config = {
        "api_endpoint": "http://testapi",
        "api_key": "whisper-key",
        "include_srt": False,
        "timeout": 5,
        "action": "translate",
        "steps": {"storages": ["s3_storage"]}
    }
    mock_s3 = MagicMock(spec=S3Storage)
    mock_s3.get_cdn_url.return_value = "http://s3.example.com/media.mp3"
    instance = WhisperEnricher()
    instance.name = "whisper_enricher"
    instance.display_name = "Whisper Enricher"
    instance.config_setup({instance.name: config})
    # bypassing the setup method and mocking S3 setup
    instance.stores = config['steps']['storages']
    instance.s3 = mock_s3
    yield instance, mock_s3


@pytest.fixture
def metadata():
    metadata = Metadata()
    metadata.set_url("http://test.url")
    metadata.set_title("test title")
    return metadata


@pytest.fixture
def mock_requests():
    with patch("auto_archiver.modules.whisper_enricher.whisper_enricher.requests") as mock_requests:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "job123"}
        mock_requests.post.return_value = mock_response
        yield mock_requests


def test_successful_job_submission(enricher, metadata, mock_requests):
    """Test successful media processing with S3 configured"""
    whisper, mock_s3 = enricher
    # Configure mock S3 URL to match test expectation
    mock_s3.get_cdn_url.return_value = "http://cdn.example.com/test.mp4"

    # Create test media with matching CDN URL
    m = Media("test.mp4")
    m.mimetype = "video/mp4"
    m.add_url(mock_s3.get_cdn_url.return_value)
    metadata.media = [m]

    # Mock the complete API interaction chain
    mock_status_response = MagicMock()
    mock_status_response.status_code = 200
    mock_status_response.json.return_value = {
        "status": "success",
        "meta": {}
    }
    mock_artifacts_response = MagicMock()
    mock_artifacts_response.status_code = 200
    mock_artifacts_response.json.return_value = [{
        "data": [{"start": 0, "end": 5, "text": "test transcript"}]
    }]
    # Set up mock response sequence
    mock_requests.get.side_effect = [
        mock_status_response,  # First call: status check
        mock_artifacts_response  # Second call: artifacts check
    ]
    # Run enrichment (without opening file)
    whisper.enrich(metadata)
    # Check API interactions
    mock_requests.post.assert_called_once_with(
        "http://testapi/jobs",
        json={"url": "http://cdn.example.com/test.mp4", "type": "translate"},
        headers={"Authorization": "Bearer whisper-key"}
    )
    # Verify job status checks
    assert mock_requests.get.call_count == 2
    assert "artifact_0_text" in metadata.media[0].get("whisper_model")
    assert "test transcript" in metadata.metadata.get("content")

