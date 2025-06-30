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
