import os
from datetime import date

import pytest

from .test_extractor_base import TestExtractorBase
from auto_archiver.modules.telethon_extractor import TelethonExtractor


class TestTelethonExtractor(TestExtractorBase):
    extractor_module = "telethon_extractor"
    extractor: TelethonExtractor
    config = {
        "api_id": 123,
        "api_hash": "ABC",
    }

    @pytest.fixture(autouse=True)
    def mock_client_setup(self, mocker):
        mocker.patch("telethon.client.auth.AuthMethods.start")

    def test_setup_fails_clear_session_file(self, get_lazy_module, tmp_path, mocker):
        start = mocker.patch("telethon.client.auth.AuthMethods.start")
        start.side_effect = Exception("Test exception")

        # make sure the default setup file is created
        session_file = tmp_path / "test.session"

        lazy_module = get_lazy_module("telethon_extractor")

        with pytest.raises(Exception):
            lazy_module.load(
                {"telethon_extractor": {"session_file": str(session_file), "api_id": 123, "api_hash": "ABC"}}
            )

        assert session_file.exists()
        assert f"telethon-{date.today().strftime('%Y-%m-%d')}" in lazy_module._instance.session_file
        assert os.path.exists(lazy_module._instance.session_file + ".session")
