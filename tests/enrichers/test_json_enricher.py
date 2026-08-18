"""
Tests for the JsonEnricher module
"""

import json
import os
import pytest


@pytest.fixture
def json_enricher(setup_module):
    return setup_module("json_enricher")


class TestJsonEnricher:
    """Test the JsonEnricher functionality."""

    def test_enrich_creates_json_file(self, json_enricher, make_item):
        """Test that enrich creates a metadata.json file."""
        item = make_item("https://example.com/test")
        item.set("title", "Test Title")
        item.set("description", "Test description")

        json_enricher.enrich(item)

        # Check that a media with id 'metadata_json' was added
        json_media = item.get_media_by_id("metadata_json")
        assert json_media is not None
        assert json_media.filename.endswith("metadata.json")
        assert os.path.exists(json_media.filename)

    def test_enrich_json_content(self, json_enricher, make_item):
        """Test that the JSON content is correct."""
        item = make_item("https://example.com/test")
        item.set("title", "Test Title")
        item.set("custom_field", "custom_value")

        json_enricher.enrich(item)

        json_media = item.get_media_by_id("metadata_json")
        with open(json_media.filename, "r", encoding="utf-8") as f:
            content = json.load(f)

        # The to_dict() returns nested structure: {status, metadata: {...}, media: [...]}
        assert content["metadata"]["title"] == "Test Title"
        assert content["metadata"]["custom_field"] == "custom_value"
        assert content["metadata"]["url"] == "https://example.com/test"

    def test_enrich_handles_special_characters(self, json_enricher, make_item):
        """Test that special characters are handled correctly."""
        item = make_item("https://example.com/test")
        item.set("title", "Test with émojis 🎉 and üñíçödé")

        json_enricher.enrich(item)

        json_media = item.get_media_by_id("metadata_json")
        with open(json_media.filename, "r", encoding="utf-8") as f:
            content = json.load(f)

        # Access the nested metadata structure
        assert "émojis 🎉" in content["metadata"]["title"]
        assert "üñíçödé" in content["metadata"]["title"]

    def test_enrich_empty_metadata(self, json_enricher, make_item):
        """Test enriching metadata with minimal content."""
        item = make_item("https://example.com/minimal")

        json_enricher.enrich(item)

        json_media = item.get_media_by_id("metadata_json")
        assert json_media is not None
        assert os.path.exists(json_media.filename)
