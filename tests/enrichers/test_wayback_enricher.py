import json
import requests
import pytest
from auto_archiver.modules.wayback_extractor_enricher import WaybackExtractorEnricher
from auto_archiver.core import Metadata


@pytest.fixture(autouse=True)
def mock_sleep(mocker):
    """Mock time.sleep to avoid delays."""
    return mocker.patch("time.sleep")


@pytest.fixture
def mock_is_auth_wall(mocker):
    """Fixture to mock is_auth_wall behavior."""

    def _mock_is_auth_wall(return_value: bool):
        return mocker.patch("auto_archiver.utils.url.is_auth_wall", return_value=return_value)

    return _mock_is_auth_wall


@pytest.fixture
def mock_post_success(mocker):
    """Fixture to mock POST requests with a successful response."""

    def _mock_post(json_data: dict = None, status_code: int = 200):
        json_data = {"job_id": "job123"} if json_data is None else json_data
        resp = mocker.Mock(status_code=status_code)
        resp.json.return_value = json_data
        return mocker.patch("requests.post", return_value=resp)

    return _mock_post


@pytest.fixture
def mock_get_success(mocker):
    """Fixture to mock GET requests returning a completed archive status."""

    def _mock_get(json_data: dict = None, status_code: int = 200):
        json_data = json_data or {
            "status": "success",
            "timestamp": "20250101010101",
            "original_url": "https://example.com",
        }
        resp = mocker.Mock(status_code=status_code)
        resp.json.return_value = json_data
        return mocker.patch("requests.get", return_value=resp)

    return _mock_get


@pytest.fixture
def wayback_extractor_enricher(setup_module) -> WaybackExtractorEnricher:
    configs: dict = {
        "timeout": 5,
        "if_not_archived_within": None,
        "key": "somekey",
        "secret": "secret",
        "proxy_http": None,
        "proxy_https": None,
    }
    return setup_module("wayback_extractor_enricher", configs)


def test_download_success(wayback_extractor_enricher, mock_is_auth_wall, mock_post_success, mock_get_success):
    mock_is_auth_wall(False)
    mock_post_success()
    mock_get_success()
    # Basic metadata to allow merge
    metadata = Metadata().set_url("https://example.com")
    result = wayback_extractor_enricher.download(metadata)
    assert result.get("wayback") == "https://web.archive.org/web/20250101010101/https://example.com"


def test_enrich_auth_wall(wayback_extractor_enricher, metadata, mock_is_auth_wall):
    mock_is_auth_wall(True)
    result = wayback_extractor_enricher.enrich(metadata)
    assert result is None


def test_enrich_already_enriched(wayback_extractor_enricher, metadata):
    metadata.set("wayback", "existing")
    result = wayback_extractor_enricher.enrich(metadata)
    assert result is True


def test_enrich_post_failure(wayback_extractor_enricher, metadata, mock_is_auth_wall, mock_post_success):
    mock_is_auth_wall(False)
    mock_post_success(json_data={"error": "server error"}, status_code=500)
    result = wayback_extractor_enricher.enrich(metadata)
    assert result is False
    assert "Internet archive failed with status of 500" in metadata.get("wayback")


def test_enrich_post_json_decode_error(wayback_extractor_enricher, metadata, mock_is_auth_wall, mocker):
    mock_is_auth_wall(False)
    resp = mocker.Mock(status_code=200)
    resp.json.side_effect = json.decoder.JSONDecodeError("msg", "doc", 0)
    resp.text = "invalid json"
    mocker.patch("requests.post", return_value=resp)
    assert wayback_extractor_enricher.enrich(metadata) is False


def test_enrich_no_job_id(wayback_extractor_enricher, metadata, mock_is_auth_wall, mock_post_success):
    mock_is_auth_wall(False)
    mock_post_success(json_data={})
    assert wayback_extractor_enricher.enrich(metadata) is False


def test_enrich_get_success(
    wayback_extractor_enricher, metadata, mock_is_auth_wall, mock_post_success, mock_get_success
):
    mock_is_auth_wall(False)
    mock_post_success()
    mock_get_success()
    assert wayback_extractor_enricher.enrich(metadata) is True
    assert metadata.get("wayback") == "https://web.archive.org/web/20250101010101/https://example.com"
    assert metadata.get("check wayback") == "https://web.archive.org/web/*/https://example.com"


def test_enrich_get_failure(
    wayback_extractor_enricher, metadata, mock_is_auth_wall, mock_post_success, mock_get_success
):
    mock_is_auth_wall(False)
    mock_post_success()
    mock_get_success(json_data={"status": "failed"}, status_code=400)
    assert wayback_extractor_enricher.enrich(metadata) is False


def test_enrich_get_request_exception(
    wayback_extractor_enricher, metadata, mock_is_auth_wall, mock_post_success, mocker
):
    mock_is_auth_wall(False)
    mock_post_success()
    mocker.patch("requests.get", side_effect=requests.exceptions.RequestException("error"))
    mocker.patch("time.sleep", return_value=None)
    # check it still enriches the job_id information
    assert wayback_extractor_enricher.enrich(metadata) is True
    assert metadata.get("wayback").get("job_id") == "job123"


def test_enrich_get_json_decode_error(
    wayback_extractor_enricher, metadata, mock_is_auth_wall, mock_post_success, mocker
):
    mock_is_auth_wall(False)
    mock_post_success()
    resp = mocker.Mock()
    resp.json.side_effect = json.decoder.JSONDecodeError("msg", "doc", 0)
    resp.text = "invalid json"
    mocker.patch("requests.get", return_value=resp)
    mocker.patch("time.sleep", return_value=None)
    # check it still enriches the job_id information
    assert wayback_extractor_enricher.enrich(metadata) is True
    assert metadata.get("wayback").get("job_id") == "job123"
