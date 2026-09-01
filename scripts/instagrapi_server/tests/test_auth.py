"""Tests for the instaserver API-key authentication.

Run from scripts/instagrapi_server with:
    poetry install --no-root --with dev
    poetry run pytest

These tests are skipped automatically when fastapi/httpx are not installed
(e.g. in the main auto-archiver test suite, which does not depend on them).
"""

import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

SERVER_FILE = Path(__file__).parent.parent / "src" / "instaserver.py"
API_KEY = "test-api-key"


class FakeMedia:
    def model_dump(self):
        return {"id": "123"}


class FakeClient:
    def load_settings(self, path):
        pass

    def get_timeline_feed(self):
        pass

    def login(self, username, password):
        pass

    def dump_settings(self, path):
        Path(path).write_text("{}")

    def media_info(self, media_id):
        return FakeMedia()


@pytest.fixture
def stub_instagrapi(monkeypatch):
    """Stands in for the instagrapi package so no real Instagram calls happen."""
    instagrapi = types.ModuleType("instagrapi")
    instagrapi.Client = FakeClient
    exceptions = types.ModuleType("instagrapi.exceptions")
    exceptions.LoginRequired = type("LoginRequired", (Exception,), {})
    exceptions.BadCredentials = type("BadCredentials", (Exception,), {})
    monkeypatch.setitem(sys.modules, "instagrapi", instagrapi)
    monkeypatch.setitem(sys.modules, "instagrapi.exceptions", exceptions)


def load_server(monkeypatch, tmp_path, api_key):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "secrets").mkdir()
    monkeypatch.setenv("INSTAGRAM_USERNAME", "user")
    monkeypatch.setenv("INSTAGRAM_PASSWORD", "pass")
    if api_key is None:
        monkeypatch.delenv("INSTAGRAPI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("INSTAGRAPI_API_KEY", api_key)
    spec = importlib.util.spec_from_file_location("instaserver_under_test", SERVER_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def server(stub_instagrapi, monkeypatch, tmp_path):
    return load_server(monkeypatch, tmp_path, API_KEY)


def test_request_without_key_is_rejected(server):
    with TestClient(server.app) as client:
        response = client.get("/v1/media/by/id", params={"id": "123"})
    assert response.status_code == 401


def test_request_with_wrong_key_is_rejected(server):
    with TestClient(server.app) as client:
        response = client.get("/v1/media/by/id", params={"id": "123"}, headers={"x-access-key": "wrong"})
    assert response.status_code == 401


def test_request_with_valid_key_is_accepted(server):
    with TestClient(server.app) as client:
        response = client.get("/v1/media/by/id", params={"id": "123"}, headers={"x-access-key": API_KEY})
    assert response.status_code == 200
    assert response.json() == {"id": "123"}


def test_session_file_permissions(server):
    with TestClient(server.app):
        pass
    mode = os.stat("secrets/instagrapi_session.json").st_mode & 0o777
    assert mode == 0o600


def test_startup_refuses_without_api_key(stub_instagrapi, monkeypatch, tmp_path):
    server = load_server(monkeypatch, tmp_path, api_key=None)
    with pytest.raises(SystemExit):
        server.startup_event()


def test_empty_configured_key_rejects_all_requests(stub_instagrapi, monkeypatch, tmp_path):
    """Even if startup were bypassed, an empty key must never authenticate."""
    server = load_server(monkeypatch, tmp_path, api_key="")
    with pytest.raises(HTTPException) as exc_info:
        server.verify_access_key("")
    assert exc_info.value.status_code == 401
