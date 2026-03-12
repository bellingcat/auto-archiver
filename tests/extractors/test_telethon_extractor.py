import asyncio
import os
from datetime import date

import pytest

from auto_archiver.modules.telethon_extractor.telethon_extractor import TelethonExtractor


@pytest.fixture(autouse=True)
def mock_client_setup(mocker):
    mocker.patch("telethon.client.auth.AuthMethods.start")


def test_setup_fails_clear_session_file(get_lazy_module, tmp_path, mocker):
    start = mocker.patch("telethon.client.auth.AuthMethods.start")
    start.side_effect = Exception("Test exception")

    # make sure the default setup file is created
    session_file = tmp_path / "test.session"

    lazy_module = get_lazy_module("telethon_extractor")

    with pytest.raises(Exception):
        lazy_module.load({"telethon_extractor": {"session_file": str(session_file), "api_id": 123, "api_hash": "ABC"}})

    assert session_file.exists()
    assert f"telethon-{date.today().strftime('%Y-%m-%d')}" in lazy_module._instance.session_file
    assert os.path.exists(lazy_module._instance.session_file + ".session")


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://t.me/channel/123", True),
        ("https://t.me/c/123/456", True),
        ("https://t.me/channel/s/789", True),
        ("https://t.me/c/123/s/456", True),
        ("https://t.me/with_single/1234567?single", True),
        ("https://t.me/invalid", False),
        ("https://example.com/nottelegram/123", False),
    ],
)
def test_valid_url_regex(url, expected, get_lazy_module):
    match = TelethonExtractor.valid_url.search(url)
    assert bool(match) == expected


@pytest.mark.parametrize(
    "invite,expected",
    [
        ("t.me/joinchat/AAAAAE", True),
        ("t.me/+AAAAAE", True),
        ("t.me/AAAAAE", True),
        ("https://t.me/joinchat/AAAAAE", True),
        ("https://t.me/+AAAAAE", True),
        ("https://t.me/AAAAAE", True),
        ("https://example.com/AAAAAE", False),
    ],
)
def test_invite_pattern_regex(invite, expected, get_lazy_module):
    match = TelethonExtractor.invite_pattern.search(invite)
    assert bool(match) == expected


def test_setup_with_closed_event_loop(get_lazy_module, tmp_path, mocker):
    """
    Simulate the Celery worker scenario where the asyncio event loop is closed
    before setup() runs. The fix should create a new event loop so that
    TelegramClient.start() does not raise 'Event loop is closed'.
    """
    # create a session file so setup doesn't fail on missing file
    session_file = tmp_path / "test.session"
    session_file.touch()

    # close the current event loop to simulate a Celery worker environment
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.close()

    lazy_module = get_lazy_module("telethon_extractor")
    module = lazy_module.load(
        {"telethon_extractor": {"session_file": str(session_file), "api_id": 123, "api_hash": "ABC"}}
    )

    # setup should have succeeded and a new open event loop should exist
    new_loop = asyncio.get_event_loop()
    assert not new_loop.is_closed()
    assert module.client is not None


def test_setup_with_no_event_loop(get_lazy_module, tmp_path, mocker):
    """
    Simulate the scenario where there is no current event loop at all
    (e.g. running in a non-main thread). The fix should create one.
    """
    session_file = tmp_path / "test.session"
    session_file.touch()

    # Remove the current event loop entirely
    # In Python 3.12+, get_event_loop() in a non-main thread raises RuntimeError
    mocker.patch("asyncio.get_event_loop", side_effect=RuntimeError("no current event loop"))
    new_loop_mock = mocker.MagicMock()
    new_loop_mock.is_closed.return_value = False
    mocker.patch("asyncio.new_event_loop", return_value=new_loop_mock)
    set_loop = mocker.patch("asyncio.set_event_loop")

    lazy_module = get_lazy_module("telethon_extractor")
    lazy_module.load({"telethon_extractor": {"session_file": str(session_file), "api_id": 123, "api_hash": "ABC"}})

    # a new event loop should have been created and set
    asyncio.new_event_loop.assert_called_once()
    set_loop.assert_called_once_with(new_loop_mock)
