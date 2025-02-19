import pytest
from auto_archiver.modules.atlos_feeder import AtlosFeeder


class FakeAPIResponse:
    """Simulate a response object."""

    def __init__(self, data: dict, raise_error: bool = False) -> None:
        self._data = data
        self.raise_error = raise_error

    def json(self) -> dict:
        return self._data

    def raise_for_status(self) -> None:
        if self.raise_error:
            raise Exception("HTTP error")


@pytest.fixture
def atlos_feeder(setup_module) -> AtlosFeeder:
    """Fixture for AtlosFeeder."""
    configs: dict = {
        "api_token": "abc123",
        "atlos_url": "https://platform.atlos.org",
    }
    return setup_module("atlos_feeder", configs)


@pytest.fixture
def mock_atlos_api(mocker):
    """Fixture to mock requests to Atlos API."""
    def _mock_responses(responses):
        mocker.patch(
            "requests.get",
            side_effect=[FakeAPIResponse(data) for data in responses],
        )
    return _mock_responses


def test_atlos_feeder_iter_yields_valid_metadata(atlos_feeder, mock_atlos_api):
    """Test valid items are yielded and invalid ones ignored."""
    mock_atlos_api([
        {
            "next": None,
            "results": [
                {"source_url": "http://example.com", "id": 1,
                 "metadata": {"auto_archiver": {"processed": False}},
                 "visibility": "visible", "status": "complete"},
                {"source_url": "", "id": 2,
                 "metadata": {"auto_archiver": {"processed": False}},
                 "visibility": "visible", "status": "complete"},
                {"source_url": "http://example.org", "id": 3,
                 "metadata": {"auto_archiver": {"processed": True}},
                 "visibility": "visible", "status": "complete"},
            ],
        }
    ])

    items = list(atlos_feeder)
    assert len(items) == 1
    assert items[0].get_url() == "http://example.com"
    assert items[0].get("atlos_id") == 1


def test_atlos_feeder_multiple_pages(atlos_feeder, mock_atlos_api):
    """Test iteration over multiple pages with valid items."""
    mock_atlos_api([
        {
            "next": "cursor2",
            "results": [
                {"source_url": "http://example1.com", "id": 10,
                 "metadata": {"auto_archiver": {"processed": False}},
                 "visibility": "visible", "status": "complete"},
            ],
        },
        {
            "next": None,
            "results": [
                {"source_url": "http://example2.com", "id": 20,
                 "metadata": {"auto_archiver": {"processed": False}},
                 "visibility": "visible", "status": "complete"},
            ],
        },
    ])

    items = list(atlos_feeder)
    assert len(items) == 2
    assert items[0].get_url() == "http://example1.com"
    assert items[0].get("atlos_id") == 10
    assert items[1].get_url() == "http://example2.com"
    assert items[1].get("atlos_id") == 20


def test_atlos_feeder_no_results(atlos_feeder, mock_atlos_api):
    """Test iteration stops when no results are returned."""
    mock_atlos_api([{"next": None, "results": []}])
    assert list(atlos_feeder) == []


def test_atlos_feeder_http_error(atlos_feeder, mocker):
    """Test raises an exception on HTTP error."""
    mocker.patch(
        "requests.get",
        return_value=FakeAPIResponse({"next": None, "results": []}, raise_error=True),
    )
    with pytest.raises(Exception, match="HTTP error"):
        list(atlos_feeder)
