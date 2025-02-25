from datetime import datetime, timezone
import pytest

from auto_archiver.core import Metadata, Media
from auto_archiver.modules.gsheet_feeder_db import GsheetsFeederDB, GWorksheet


@pytest.fixture
def mock_gworksheet(mocker):
    mock_gworksheet = mocker.MagicMock(spec=GWorksheet)
    mock_gworksheet.col_exists.return_value = True
    mock_gworksheet.get_cell.return_value = ""
    mock_gworksheet.get_row.return_value = {}
    return mock_gworksheet


@pytest.fixture
def mock_metadata(mocker):
    metadata: Metadata = mocker.MagicMock(spec=Metadata)
    metadata.get_url.return_value = "http://example.com"
    metadata.status = "done"
    metadata.get_title.return_value = "Example Title"
    metadata.get.return_value = "Example Content"
    metadata.get_timestamp.return_value = "2025-01-01T00:00:00"
    metadata.get_final_media.return_value = mocker.MagicMock(spec=Media)
    metadata.get_all_media.return_value = []
    metadata.get_media_by_id.return_value = None
    metadata.get_first_image.return_value = None
    return metadata

@pytest.fixture
def metadata():
    metadata = Metadata()
    metadata.add_media(Media(filename="screenshot", urls=["http://example.com/screenshot.png"]))
    metadata.add_media(Media(filename="browsertrix", urls=["http://example.com/browsertrix.wacz"]))
    metadata.add_media(Media(filename="thumbnail", urls=["http://example.com/thumbnail.png"]))
    metadata.set_url("http://example.com")
    metadata.set_title("Example Title")
    metadata.set_content("Example Content")
    metadata.success("my-archiver")
    metadata.set("timestamp", "2025-01-01T00:00:00")
    metadata.set("date", "2025-02-04T18:22:24.909112+00:00")
    return metadata


@pytest.fixture
def mock_media(mocker):
    """Fixture for a mock Media object."""
    mock_media = mocker.MagicMock(spec=Media)
    mock_media.urls = ["http://example.com/media"]
    mock_media.get.return_value = "not-calculated"
    return mock_media

@pytest.fixture
def gsheets_db(mock_gworksheet, setup_module, mocker):
    mocker.patch("gspread.service_account")
    config: dict = {
        "sheet": "testsheet",
        "sheet_id": None,
        "header": 1,
        "service_account": "test/service_account.json",
        "columns": {'url': 'link', 'status': 'archive status', 'folder': 'destination folder', 'archive': 'archive location', 'date': 'archive date', 'thumbnail': 'thumbnail', 'timestamp': 'upload timestamp', 'title': 'upload title', 'text': 'text content', 'screenshot': 'screenshot', 'hash': 'hash', 'pdq_hash': 'perceptual hashes', 'wacz': 'wacz', 'replaywebpage': 'replaywebpage'},
        "allow_worksheets": set(),
        "block_worksheets": set(),
        "use_sheet_names_in_stored_paths": True,
    }
    db = setup_module("gsheet_feeder_db", config)
    db._retrieve_gsheet = mocker.MagicMock(return_value=(mock_gworksheet, 1))
    return db


@pytest.fixture
def fixed_timestamp():
    """Fixture for a fixed timestamp."""
    return datetime(2025, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def expected_calls(mock_media, fixed_timestamp):
    """Fixture for the expected cell updates."""
    return  [
        (1, 'status', 'my-archiver: success'),
        (1, 'archive', 'http://example.com/screenshot.png'),
        (1, 'date', '2025-02-01T00:00:00+00:00'),
        (1, 'title', 'Example Title'),
        (1, 'text', 'Example Content'),
        (1, 'timestamp', '2025-01-01T00:00:00+00:00'),
        (1, 'hash', 'not-calculated'),
        # (1, 'screenshot', 'http://example.com/screenshot.png'),
        # (1, 'thumbnail', '=IMAGE("http://example.com/thumbnail.png")'),
        # (1, 'wacz', 'http://example.com/browsertrix.wacz'),
        # (1, 'replaywebpage', 'https://replayweb.page/?source=http%3A%2F%2Fexample.com%2Fbrowsertrix.wacz#view=pages&url=')
    ]

def test_retrieve_gsheet(gsheets_db, metadata, mock_gworksheet):
    gw, row = gsheets_db._retrieve_gsheet(metadata)
    assert gw == mock_gworksheet
    assert row == 1


def test_started(gsheets_db, mock_metadata, mock_gworksheet):
    gsheets_db.started(mock_metadata)
    mock_gworksheet.set_cell.assert_called_once_with(1, 'status', 'Archive in progress')

def test_failed(gsheets_db, mock_metadata, mock_gworksheet):
    reason = "Test failure"
    gsheets_db.failed(mock_metadata, reason)
    mock_gworksheet.set_cell.assert_called_once_with(1, 'status', f'Archive failed {reason}')


def test_aborted(gsheets_db, mock_metadata, mock_gworksheet):
    gsheets_db.aborted(mock_metadata)
    mock_gworksheet.set_cell.assert_called_once_with(1, 'status', '')


def test_done(gsheets_db, metadata, mock_gworksheet, expected_calls, mocker):
    mocker.patch("auto_archiver.modules.gsheet_feeder_db.gsheet_feeder_db.get_current_timestamp", return_value='2025-02-01T00:00:00+00:00')
    gsheets_db.done(metadata)
    mock_gworksheet.batch_set_cell.assert_called_once_with(expected_calls)


def test_done_cached(gsheets_db, metadata, mock_gworksheet, mocker):
    mocker.patch("auto_archiver.modules.gsheet_feeder_db.gsheet_feeder_db.get_current_timestamp", return_value='2025-02-01T00:00:00+00:00')
    gsheets_db.done(metadata, cached=True)

    # Verify the status message includes "[cached]"
    call_args = mock_gworksheet.batch_set_cell.call_args[0][0]
    assert any(call[2].startswith("[cached]") for call in call_args)


def test_done_missing_media(gsheets_db, metadata, mock_gworksheet, mocker):
    # clear media from metadata
    metadata.media = []
    mocker.patch("auto_archiver.modules.gsheet_feeder_db.gsheet_feeder_db.get_current_timestamp", return_value='2025-02-01T00:00:00+00:00')
    gsheets_db.done(metadata)
    # Verify nothing media-related gets updated
    call_args = mock_gworksheet.batch_set_cell.call_args[0][0]
    media_fields = {'archive', 'screenshot', 'thumbnail', 'wacz', 'replaywebpage'}
    assert all(call[1] not in media_fields for call in call_args)

def test_safe_status_update(gsheets_db, metadata, mock_gworksheet):
    gsheets_db._safe_status_update(metadata, "Test status")
    mock_gworksheet.set_cell.assert_called_once_with(1, 'status', 'Test status')


