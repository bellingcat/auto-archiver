"""
Tests for the CLIFeeder module
"""

import pytest

from auto_archiver.modules.cli_feeder.cli_feeder import CLIFeeder
from auto_archiver.core.consts import SetupError
from auto_archiver.core.metadata import Metadata


@pytest.fixture
def cli_feeder_instance():
    """Create a CLIFeeder instance with mocked config."""

    def _create(urls):
        feeder = CLIFeeder()
        # Mock the config structure that cli_feeder expects
        feeder.config = {"urls": urls}
        feeder.name = "cli_feeder"
        feeder.tmp_dir = "/tmp"
        return feeder

    return _create


class TestCLIFeeder:
    """Test the CLIFeeder functionality."""

    def test_iter_yields_metadata_for_urls(self, cli_feeder_instance):
        """Test that iteration yields Metadata objects for each URL."""
        urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
        feeder = cli_feeder_instance(urls)
        feeder.setup()

        items = list(feeder)

        assert len(items) == 3
        assert all(isinstance(item, Metadata) for item in items)
        assert items[0].get_url() == "https://example.com/1"
        assert items[1].get_url() == "https://example.com/2"
        assert items[2].get_url() == "https://example.com/3"

    def test_iter_single_url(self, cli_feeder_instance):
        """Test iteration with a single URL."""
        feeder = cli_feeder_instance(["https://example.com/single"])
        feeder.setup()

        items = list(feeder)

        assert len(items) == 1
        assert items[0].get_url() == "https://example.com/single"

    def test_setup_raises_without_urls(self, cli_feeder_instance):
        """Test that setup raises SetupError when no URLs provided."""
        feeder = cli_feeder_instance([])

        with pytest.raises(SetupError) as exc_info:
            feeder.setup()

        assert "No URLs provided" in str(exc_info.value)

    def test_setup_raises_with_none_urls(self, cli_feeder_instance):
        """Test that setup raises SetupError when urls is None."""
        feeder = cli_feeder_instance(None)

        with pytest.raises(SetupError) as exc_info:
            feeder.setup()

        assert "No URLs provided" in str(exc_info.value)
