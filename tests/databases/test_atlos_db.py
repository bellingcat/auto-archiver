import pytest
from datetime import datetime

from auto_archiver.core import Metadata
from auto_archiver.modules.atlos_db import AtlosDb


class FakeAPIResponse:
    """Simulate a response object."""

    def __init__(self, data: dict, raise_error: bool = False) -> None:
        self._data = data
        self.raise_error = raise_error

    def raise_for_status(self) -> None:
        if self.raise_error:
            raise Exception("HTTP error")


@pytest.fixture
def atlos_db(setup_module) -> AtlosDb:
    """Fixture for AtlosDb."""
    configs: dict = {
        "api_token": "abc123",
        "atlos_url": "https://platform.atlos.org",
    }
    return setup_module("atlos_db", configs)


def test_failed_no_atlos_id(atlos_db, metadata, mocker):
    """Test failed() skips posting when no atlos_id present."""
    post_mock = mocker.patch("requests.post")
    atlos_db.failed(metadata, "failure reason")
    post_mock.assert_not_called()


def test_failed_with_atlos_id(atlos_db, metadata, mocker):
    """Test failed() posts failure when atlos_id is present."""
    metadata.set("atlos_id", 42)
    fake_resp = FakeAPIResponse({}, raise_error=False)
    post_mock = mocker.patch("requests.post", return_value=fake_resp)
    atlos_db.failed(metadata, "failure reason")
    expected_url = (
        f"{atlos_db.atlos_url}/api/v2/source_material/metadata/42/auto_archiver"
    )
    expected_headers = {"Authorization": f"Bearer {atlos_db.api_token}"}
    expected_json = {
        "metadata": {"processed": True, "status": "error", "error": "failure reason"}
    }
    post_mock.assert_called_once_with(
        expected_url, headers=expected_headers, json=expected_json
    )


def test_failed_http_error(atlos_db, metadata, mocker):
    """Test failed() raises exception on HTTP error."""
    metadata.set("atlos_id", 42)
    fake_resp = FakeAPIResponse({}, raise_error=True)
    mocker.patch("requests.post", return_value=fake_resp)
    with pytest.raises(Exception, match="HTTP error"):
        atlos_db.failed(metadata, "failure reason")


def test_fetch_returns_false(atlos_db):
    """Test fetch() always returns False."""
    item = Metadata()
    assert atlos_db.fetch(item) is False


def test_done_no_atlos_id(atlos_db, mocker):
    """Test done() skips posting when no atlos_id present."""
    item = Metadata().set_url("http://example.com")
    post_mock = mocker.patch("requests.post")
    atlos_db.done(item)
    post_mock.assert_not_called()


def test_done_with_atlos_id(atlos_db, metadata, mocker):
    """Test done() posts success when atlos_id is present."""
    metadata.set("atlos_id", 99)
    now = datetime.now()
    metadata.set("timestamp", now)
    fake_resp = FakeAPIResponse({}, raise_error=False)
    post_mock = mocker.patch("requests.post", return_value=fake_resp)
    atlos_db.done(metadata)
    expected_url = (
        f"{atlos_db.atlos_url}/api/v2/source_material/metadata/99/auto_archiver"
    )
    expected_headers = {"Authorization": f"Bearer {atlos_db.api_token}"}
    expected_results = metadata.metadata.copy()
    expected_results["timestamp"] = now.isoformat()
    expected_json = {
        "metadata": {
            "processed": True,
            "status": "success",
            "results": expected_results,
        }
    }
    post_mock.assert_called_once_with(
        expected_url, headers=expected_headers, json=expected_json
    )


def test_done_http_error(atlos_db, metadata, mocker):
    """Test done() raises exception on HTTP error."""
    metadata.set("atlos_id", 123)
    fake_resp = FakeAPIResponse({}, raise_error=True)
    mocker.patch("requests.post", return_value=fake_resp)
    with pytest.raises(Exception, match="HTTP error"):
        atlos_db.done(metadata)
