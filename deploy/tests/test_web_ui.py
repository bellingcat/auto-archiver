"""Tests for deploy/web_ui.py – FastAPI web interface."""

from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset in-memory state between tests."""
    import deploy.web_ui as mod

    mod._valid_sessions.clear()
    mod._jobs.clear()
    yield
    mod._valid_sessions.clear()
    mod._jobs.clear()


@pytest.fixture
def client_no_auth():
    """Test client with auth disabled (no AUTH_PASSWORD)."""
    with patch.object(__import__("deploy.web_ui", fromlist=["web_ui"]), "AUTH_PASSWORD", ""):
        from deploy.web_ui import app

        yield TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client_with_auth():
    """Test client with auth enabled."""
    with patch.object(__import__("deploy.web_ui", fromlist=["web_ui"]), "AUTH_PASSWORD", "secret123"):
        from deploy.web_ui import app

        yield TestClient(app, raise_server_exceptions=False)


def _login(client, password="secret123"):
    """Helper: log in and return the session cookie."""
    resp = client.post("/login", data={"password": password}, follow_redirects=False)
    return resp.cookies.get("aa_session")


# ── Health check ──────────────────────────────────────────────────────


class TestHealthCheck:
    def test_status_returns_ok(self, client_no_auth):
        resp = client_no_auth.get("/status")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_status_no_auth_required(self, client_with_auth):
        resp = client_with_auth.get("/status")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ── Auth disabled ─────────────────────────────────────────────────────


class TestNoAuth:
    def test_index_accessible(self, client_no_auth):
        resp = client_no_auth.get("/")
        assert resp.status_code == 200
        assert "Auto Archiver" in resp.text

    def test_login_page_redirects_to_index(self, client_no_auth):
        resp = client_no_auth.get("/login", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/"

    def test_login_post_redirects_to_index(self, client_no_auth):
        resp = client_no_auth.post("/login", data={"password": "anything"}, follow_redirects=False)
        assert resp.status_code == 302

    def test_no_logout_link_shown(self, client_no_auth):
        resp = client_no_auth.get("/")
        assert "Logout" not in resp.text


# ── Auth enabled ──────────────────────────────────────────────────────


class TestAuth:
    def test_index_redirects_to_login(self, client_with_auth):
        resp = client_with_auth.get("/", follow_redirects=False)
        assert resp.status_code == 307
        assert resp.headers["location"] == "/login"

    def test_login_page_renders(self, client_with_auth):
        resp = client_with_auth.get("/login")
        assert resp.status_code == 200
        assert "Password" in resp.text

    def test_wrong_password_returns_401(self, client_with_auth):
        resp = client_with_auth.post("/login", data={"password": "wrong"})
        assert resp.status_code == 401
        assert "Wrong password" in resp.text

    def test_correct_password_sets_cookie(self, client_with_auth):
        resp = client_with_auth.post("/login", data={"password": "secret123"}, follow_redirects=False)
        assert resp.status_code == 302
        assert "aa_session" in resp.cookies

    def test_authenticated_access(self, client_with_auth):
        cookie = _login(client_with_auth)
        client_with_auth.cookies.set("aa_session", cookie)
        resp = client_with_auth.get("/")
        assert resp.status_code == 200
        assert "Auto Archiver" in resp.text

    def test_logout_clears_session(self, client_with_auth):
        cookie = _login(client_with_auth)
        client_with_auth.cookies.set("aa_session", cookie)
        resp = client_with_auth.get("/logout", follow_redirects=False)
        assert resp.status_code == 302
        # After logout, index should redirect to login again
        client_with_auth.cookies.clear()
        resp = client_with_auth.get("/", follow_redirects=False)
        assert resp.status_code == 307

    def test_logout_link_shown_when_auth_enabled(self, client_with_auth):
        cookie = _login(client_with_auth)
        client_with_auth.cookies.set("aa_session", cookie)
        resp = client_with_auth.get("/")
        assert "Logout" in resp.text

    def test_results_requires_auth(self, client_with_auth):
        resp = client_with_auth.get("/results", follow_redirects=False)
        assert resp.status_code == 307

    def test_invalid_session_rejected(self, client_with_auth):
        client_with_auth.cookies.set("aa_session", "bogus-token")
        resp = client_with_auth.get("/", follow_redirects=False)
        assert resp.status_code == 307


# ── Archive submission ────────────────────────────────────────────────


class TestArchive:
    def test_archive_creates_job(self, client_no_auth):
        with patch("deploy.web_ui._run_archive", new_callable=AsyncMock):
            resp = client_no_auth.post(
                "/archive",
                data={"urls": "https://example.com\nhttps://example.org"},
                follow_redirects=False,
            )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"

        from deploy.web_ui import _jobs

        assert len(_jobs) == 1
        assert _jobs[0]["urls"] == ["https://example.com", "https://example.org"]
        assert _jobs[0]["status"] == "running"

    def test_archive_empty_urls_returns_400(self, client_no_auth):
        resp = client_no_auth.post("/archive", data={"urls": "   \n  \n"})
        assert resp.status_code == 400

    def test_archive_strips_whitespace(self, client_no_auth):
        with patch("deploy.web_ui._run_archive", new_callable=AsyncMock):
            client_no_auth.post(
                "/archive",
                data={"urls": "  https://example.com  \n\n  https://example.org  \n"},
                follow_redirects=False,
            )
        from deploy.web_ui import _jobs

        assert _jobs[0]["urls"] == ["https://example.com", "https://example.org"]

    def test_archive_requires_auth(self, client_with_auth):
        resp = client_with_auth.post(
            "/archive",
            data={"urls": "https://example.com"},
            follow_redirects=False,
        )
        assert resp.status_code == 307


# ── Results page ──────────────────────────────────────────────────────


class TestResults:
    def test_results_empty(self, client_no_auth, tmp_path):
        with patch("deploy.web_ui.ARCHIVE_DIR", tmp_path):
            resp = client_no_auth.get("/results")
        assert resp.status_code == 200
        assert "No archived files yet" in resp.text

    def test_results_lists_files(self, client_no_auth, tmp_path):
        (tmp_path / "test.html").write_text("<html>archived</html>")
        (tmp_path / "video.mp4").write_bytes(b"\x00" * 10)
        with patch("deploy.web_ui.ARCHIVE_DIR", tmp_path):
            resp = client_no_auth.get("/results")
        assert resp.status_code == 200
        assert "test.html" in resp.text
        assert "video.mp4" in resp.text

    def test_results_nonexistent_dir(self, client_no_auth, tmp_path):
        with patch("deploy.web_ui.ARCHIVE_DIR", tmp_path / "nonexistent"):
            resp = client_no_auth.get("/results")
        assert resp.status_code == 200
        assert "No archived files yet" in resp.text


# ── File serving ──────────────────────────────────────────────────────


class TestFileServing:
    def test_serve_existing_file(self, client_no_auth, tmp_path):
        (tmp_path / "report.html").write_text("<html>done</html>")
        with patch("deploy.web_ui.ARCHIVE_DIR", tmp_path):
            resp = client_no_auth.get("/files/report.html")
        assert resp.status_code == 200

    def test_serve_nonexistent_file(self, client_no_auth, tmp_path):
        with patch("deploy.web_ui.ARCHIVE_DIR", tmp_path):
            resp = client_no_auth.get("/files/nope.txt")
        assert resp.status_code == 404

    def test_path_traversal_blocked(self, client_no_auth, tmp_path):
        # Create a file outside the archive dir
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret")
        archive = tmp_path / "archive"
        archive.mkdir()
        # Symlink into archive pointing outside
        (archive / "escape").symlink_to(outside / "secret.txt")
        with patch("deploy.web_ui.ARCHIVE_DIR", archive):
            resp = client_no_auth.get("/files/escape")
        assert resp.status_code == 403


# ── Job rendering ─────────────────────────────────────────────────────


class TestJobRendering:
    def test_no_jobs_shows_message(self, client_no_auth):
        resp = client_no_auth.get("/")
        assert "No archiving jobs yet" in resp.text

    def test_jobs_shown_in_table(self, client_no_auth):
        from deploy.web_ui import _jobs

        _jobs.append(
            {
                "id": 1,
                "urls": ["https://example.com"],
                "status": "done",
                "started": "2026-01-01 00:00 UTC",
                "output": "",
            }
        )
        resp = client_no_auth.get("/")
        assert "example.com" in resp.text
        assert "done" in resp.text

    def test_many_urls_truncated(self, client_no_auth):
        from deploy.web_ui import _jobs

        _jobs.append(
            {
                "id": 1,
                "urls": [f"https://example.com/{i}" for i in range(10)],
                "status": "running",
                "started": "2026-01-01 00:00 UTC",
                "output": "",
            }
        )
        resp = client_no_auth.get("/")
        assert "+7 more" in resp.text


# ── HTML template rendering ──────────────────────────────────────────


class TestTemplates:
    """Verify HTML templates can be .format()-ed without KeyError."""

    def test_login_html_renders(self):
        from deploy.web_ui import LOGIN_HTML

        result = LOGIN_HTML.format(error="")
        assert "Auto Archiver" in result

    def test_login_html_renders_with_error(self):
        from deploy.web_ui import LOGIN_HTML

        result = LOGIN_HTML.format(error='<p class="err">Nope</p>')
        assert "Nope" in result

    def test_main_html_renders(self):
        from deploy.web_ui import MAIN_HTML

        result = MAIN_HTML.format(logout="", jobs_html="")
        assert "Auto Archiver" in result

    def test_results_html_renders(self):
        from deploy.web_ui import RESULTS_HTML

        result = RESULTS_HTML.format(file_list="<p>empty</p>")
        assert "Archived Files" in result
