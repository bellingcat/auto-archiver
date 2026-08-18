"""
Tests for the ConsoleDb module
"""

import pytest


@pytest.fixture
def console_db(setup_module):
    return setup_module("console_db")


class TestConsoleDb:
    """Test the ConsoleDb functionality."""

    def test_started_logs_info(self, console_db, make_item, caplog):
        """Test that started() logs an info message."""
        item = make_item("https://example.com/test")

        with caplog.at_level("INFO"):
            console_db.started(item)

        assert "STARTED" in caplog.text
        assert "example.com" in caplog.text

    def test_failed_logs_error(self, console_db, make_item, caplog):
        """Test that failed() logs an error message with reason."""
        item = make_item("https://example.com/test")
        reason = "Connection timeout"

        with caplog.at_level("ERROR"):
            console_db.failed(item, reason)

        assert "FAILED" in caplog.text
        assert "Connection timeout" in caplog.text

    def test_aborted_logs_warning(self, console_db, make_item, caplog):
        """Test that aborted() logs a warning message."""
        item = make_item("https://example.com/test")

        with caplog.at_level("WARNING"):
            console_db.aborted(item)

        assert "ABORTED" in caplog.text

    def test_done_logs_success(self, console_db, make_item, caplog):
        """Test that done() logs a success message."""
        item = make_item("https://example.com/test")

        with caplog.at_level("INFO"):
            console_db.done(item)

        assert "DONE" in caplog.text

    def test_done_cached(self, console_db, make_item, caplog):
        """Test done() with cached=True (should behave the same)."""
        item = make_item("https://example.com/test")

        with caplog.at_level("INFO"):
            console_db.done(item, cached=True)

        assert "DONE" in caplog.text
