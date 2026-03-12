"""Tests for deploy/gsheet_poller.py – background Google Sheets polling."""

import os
from unittest.mock import patch, MagicMock


from deploy.gsheet_poller import start_poller, _poll_once


# ── start_poller ──────────────────────────────────────────────────────


class TestStartPoller:
    def test_disabled_when_no_gsheet_url(self):
        """No thread should be started when GSHEET_URL is empty."""
        with (
            patch.dict(os.environ, {"GSHEET_URL": ""}, clear=False),
            patch("deploy.gsheet_poller.threading.Thread") as mock_thread,
        ):
            start_poller()
        mock_thread.assert_not_called()

    def test_disabled_when_gsheet_url_absent(self):
        env = {k: v for k, v in os.environ.items() if k != "GSHEET_URL"}
        with patch.dict(os.environ, env, clear=True), patch("deploy.gsheet_poller.threading.Thread") as mock_thread:
            start_poller()
        mock_thread.assert_not_called()

    def test_starts_thread_when_gsheet_url_set(self):
        with (
            patch.dict(os.environ, {"GSHEET_URL": "https://example.com/sheet"}, clear=False),
            patch("deploy.gsheet_poller.threading.Thread") as mock_thread,
        ):
            mock_instance = MagicMock()
            mock_thread.return_value = mock_instance
            start_poller()
        mock_thread.assert_called_once()
        assert mock_thread.call_args.kwargs["daemon"] is True
        assert mock_thread.call_args.kwargs["name"] == "gsheet-poller"
        mock_instance.start.assert_called_once()

    def test_default_interval_300(self):
        env = {"GSHEET_URL": "https://example.com/sheet"}
        # Remove POLL_INTERVAL if present
        clean_env = {k: v for k, v in os.environ.items() if k != "POLL_INTERVAL"}
        clean_env.update(env)
        with (
            patch.dict(os.environ, clean_env, clear=True),
            patch("deploy.gsheet_poller.threading.Thread") as mock_thread,
        ):
            mock_thread.return_value = MagicMock()
            start_poller()
        # interval should be passed as arg to _poll_loop
        args = mock_thread.call_args.kwargs.get("args") or mock_thread.call_args[1].get("args")
        assert args == (300,)

    def test_custom_interval(self):
        with (
            patch.dict(os.environ, {"GSHEET_URL": "x", "POLL_INTERVAL": "600"}, clear=False),
            patch("deploy.gsheet_poller.threading.Thread") as mock_thread,
        ):
            mock_thread.return_value = MagicMock()
            start_poller()
        args = mock_thread.call_args.kwargs.get("args") or mock_thread.call_args[1].get("args")
        assert args == (600,)

    def test_interval_minimum_enforced(self):
        """Intervals below 60 should be clamped to 60."""
        with (
            patch.dict(os.environ, {"GSHEET_URL": "x", "POLL_INTERVAL": "10"}, clear=False),
            patch("deploy.gsheet_poller.threading.Thread") as mock_thread,
        ):
            mock_thread.return_value = MagicMock()
            start_poller()
        args = mock_thread.call_args.kwargs.get("args") or mock_thread.call_args[1].get("args")
        assert args == (60,)


# ── _poll_once ────────────────────────────────────────────────────────


class TestPollOnce:
    def test_calls_subprocess_with_config(self):
        with patch("deploy.gsheet_poller.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            _poll_once()
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "auto_archiver" in " ".join(cmd)
        assert "--config" in cmd

    def test_handles_nonzero_exit(self):
        """Should not raise on non-zero exit, just log a warning."""
        with patch("deploy.gsheet_poller.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="some error")
            _poll_once()  # should not raise

    def test_handles_timeout(self):
        """Should not raise on timeout, just log."""
        import subprocess

        with patch("deploy.gsheet_poller.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=600)
            _poll_once()  # should not raise

    def test_handles_exception(self):
        """Should not raise on arbitrary exceptions."""
        with patch("deploy.gsheet_poller.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("broken")
            _poll_once()  # should not raise

    def test_uses_correct_config_path(self):
        with patch("deploy.gsheet_poller.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            _poll_once()
        cmd = mock_run.call_args[0][0]
        config_idx = cmd.index("--config")
        assert cmd[config_idx + 1] == "/app/secrets/orchestration.yaml"

    def test_timeout_set(self):
        with patch("deploy.gsheet_poller.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            _poll_once()
        assert mock_run.call_args[1]["timeout"] == 600
