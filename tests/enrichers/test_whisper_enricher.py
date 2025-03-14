import pytest

from auto_archiver.core import Metadata, Media
from auto_archiver.modules.s3_storage import S3Storage
from auto_archiver.modules.whisper_enricher import WhisperEnricher

TEST_S3_URL = "http://cdn.example.com/test.mp4"


@pytest.fixture(autouse=True)
def mock_sleep(mocker):
    """Mock time.sleep to avoid delays."""
    return mocker.patch("time.sleep")


@pytest.fixture
def enricher(mocker):
    """Fixture with mocked S3 and API dependencies"""
    config = {
        "api_endpoint": "http://testapi",
        "api_key": "whisper-key",
        "include_srt": False,
        "timeout": 5,
        "action": "translate",
        "steps": {"storages": ["s3_storage"]},
    }
    mock_s3 = mocker.MagicMock(spec=S3Storage)
    mock_s3.get_cdn_url.return_value = TEST_S3_URL
    instance = WhisperEnricher()
    instance.name = "whisper_enricher"
    instance.display_name = "Whisper Enricher"
    instance.config_setup({instance.name: config})
    # bypassing the setup method and mocking S3 setup
    instance.stores = config["steps"]["storages"]
    instance.s3 = mock_s3
    yield instance, mock_s3


@pytest.fixture
def metadata():
    metadata = Metadata()
    metadata.set_url("http://test.url")
    metadata.set_title("test title")
    return metadata


@pytest.fixture
def mock_requests(mocker):
    mock_requests = mocker.patch("auto_archiver.modules.whisper_enricher.whisper_enricher.requests")
    mock_response = mocker.MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "job123"}
    mock_requests.post.return_value = mock_response
    yield mock_requests


def test_successful_job_submission(enricher, metadata, mock_requests, mocker):
    """Test successful media processing with S3 configured"""
    whisper, mock_s3 = enricher
    # Configure mock S3 URL to match test expectation
    mock_s3.get_cdn_url.return_value = TEST_S3_URL

    # Create test media with matching CDN URL
    m = Media("test.mp4")
    m.mimetype = "video/mp4"
    m.add_url(mock_s3.get_cdn_url.return_value)
    metadata.media = [m]

    # Mock the complete API interaction chain
    mock_status_response = mocker.MagicMock()
    mock_status_response.status_code = 200
    mock_status_response.json.return_value = {"status": "success", "meta": {}}
    mock_artifacts_response = mocker.MagicMock()
    mock_artifacts_response.status_code = 200
    mock_artifacts_response.json.return_value = [{"data": [{"start": 0, "end": 5, "text": "test transcript"}]}]
    # Set up mock response sequence
    mock_requests.get.side_effect = [
        mock_status_response,  # First call: status check
        mock_artifacts_response,  # Second call: artifacts check
    ]

    # Run enrichment (without opening file)
    whisper.enrich(metadata)
    # Check API interactions
    mock_requests.post.assert_called_once_with(
        "http://testapi/jobs",
        json={"url": "http://cdn.example.com/test.mp4", "type": "translate"},
        headers={"Authorization": "Bearer whisper-key"},
    )
    # Verify job status checks
    assert mock_requests.get.call_count == 2
    assert "artifact_0_text" in metadata.media[0].get("whisper_model")
    assert metadata.media[0].get("whisper_model") == {
        "artifact_0_text": "test transcript",
        "job_artifacts_check": "http://testapi/jobs/job123/artifacts",
        "job_id": "job123",
        "job_status_check": "http://testapi/jobs/job123",
    }


def test_submit_job(enricher, mocker):
    """Test job submission method"""
    whisper, _ = enricher
    m = Media("test.mp4")
    m.add_url(TEST_S3_URL)
    mock_requests = mocker.patch("auto_archiver.modules.whisper_enricher.whisper_enricher.requests")
    mock_response = mocker.MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "job123"}
    mock_requests.post.return_value = mock_response
    job_id = whisper.submit_job(m)
    assert job_id == "job123"


def test_submit_raises_status(enricher, mocker):
    whisper, _ = enricher
    m = Media("test.mp4")
    m.add_url(TEST_S3_URL)
    mock_requests = mocker.patch("auto_archiver.modules.whisper_enricher.whisper_enricher.requests")
    mock_response = mocker.MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"id": "job123"}
    mock_requests.post.return_value = mock_response
    with pytest.raises(AssertionError) as exc_info:
        whisper.submit_job(m)
    assert str(exc_info.value) == "calling the whisper api http://testapi returned a non-success code: 400"


# @pytest.mark.parametrize("test_url, status", ["http://cdn.example.com/test.mp4",])
def test_submit_job_fails(enricher):
    """Test assertion fails with non-S3 URL"""
    whisper, mock_s3 = enricher
    m = Media("test.mp4")
    m.add_url("http://cdn.wrongurl.com/test.mp4")
    with pytest.raises(AssertionError):
        whisper.submit_job(m)
