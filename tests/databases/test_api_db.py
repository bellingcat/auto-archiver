import pytest

from auto_archiver.core import Metadata
from auto_archiver.modules.api_db import AAApiDb


@pytest.fixture
def api_db(setup_module):
    configs: dict = {
        "api_endpoint": "https://api.example.com",
        "api_token": "test-token",
        "public": False,
        "author_id": "Someone",
        "group_id": "123",
        "use_api_cache": True,
        "store_results": True,
        "tags": "[]",
    }
    return setup_module(AAApiDb, configs)


def test_fetch_no_cache(api_db, metadata):
    # Test fetch
    api_db.use_api_cache = False
    assert api_db.fetch(metadata) is None


def test_fetch_fail_status(api_db, metadata, mocker):
    # Test response fail in fetch method
    mock_get = mocker.patch("auto_archiver.modules.api_db.api_db.requests.get")
    mock_get.return_value.status_code = 400
    mock_get.return_value.json.return_value = {}
    mock_error = mocker.patch("loguru.logger.error")
    assert api_db.fetch(metadata) is False
    mock_error.assert_called_once_with("AA API FAIL (400): {}")


def test_fetch(api_db, metadata, mocker):
    # Test successful fetch method
    mock_get = mocker.patch("auto_archiver.modules.api_db.api_db.requests.get")
    mock_datetime = mocker.patch("auto_archiver.core.metadata.datetime.datetime")
    mock_datetime.now.return_value = "2021-01-01T00:00:00"
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{"result": {}}, {"result":
        {'media': [], 'metadata': {'_processed_at': '2021-01-01T00:00:00', 'url': 'https://example.com'},
         'status': 'no archiver'}}]
    assert api_db.fetch(metadata) == metadata


def test_done_success(api_db, metadata, mocker):
    mock_post = mocker.patch("auto_archiver.modules.api_db.api_db.requests.post")
    mock_post.return_value.status_code = 201
    api_db.done(metadata)
    mock_post.assert_called_once()
    mock_post.assert_called_once_with("https://api.example.com/interop/submit-archive",
                                      json={'author_id': 'Someone', 'url': 'https://example.com',
                                            'public': False, 'group_id': '123', 'tags': ['[', ']'], 'result': '{"status": "no archiver", "metadata": {"_processed_at": "2021-01-01T00:00:00", "url": "https://example.com"}, "media": []}'},
                                      headers={'Authorization': 'Bearer test-token'})

