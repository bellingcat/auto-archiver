"""
Tests for validators module from auto_archiver.core.validators
"""

import argparse
import json
import pytest

from auto_archiver.core.validators import positive_number, valid_file, json_loader


class TestPositiveNumber:
    """Test the positive_number validator."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (0, 0),
            (1, 1),
            (100, 100),
            (0.5, 0.5),
            (999999, 999999),
        ],
    )
    def test_positive_values(self, value, expected):
        assert positive_number(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            -1,
            -100,
            -0.5,
            -999999,
        ],
    )
    def test_negative_values_raise_error(self, value):
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            positive_number(value)
        assert "not a positive number" in str(exc_info.value)


class TestValidFile:
    """Test the valid_file validator."""

    def test_valid_file_exists(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        result = valid_file(str(test_file))
        assert result == str(test_file)

    def test_valid_file_not_exists(self):
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            valid_file("/nonexistent/path/to/file.txt")
        assert "does not exist" in str(exc_info.value)

    def test_valid_file_directory_not_file(self, tmp_path):
        # A directory is not a file
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            valid_file(str(tmp_path))
        assert "does not exist" in str(exc_info.value)


class TestJsonLoader:
    """Test the json_loader validator."""

    @pytest.mark.parametrize(
        "json_str,expected",
        [
            ('{"key": "value"}', {"key": "value"}),
            ('{"number": 123}', {"number": 123}),
            ('{"list": [1, 2, 3]}', {"list": [1, 2, 3]}),
            ('{"nested": {"inner": "value"}}', {"nested": {"inner": "value"}}),
            ("[]", []),
            ("[1, 2, 3]", [1, 2, 3]),
            ('"string"', "string"),
            ("123", 123),
            ("true", True),
            ("false", False),
            ("null", None),
        ],
    )
    def test_valid_json(self, json_str, expected):
        assert json_loader(json_str) == expected

    @pytest.mark.parametrize(
        "invalid_json",
        [
            "{invalid}",
            "{'single': 'quotes'}",
            "{missing: quotes}",
            '{"unclosed": "brace"',
            "",
        ],
    )
    def test_invalid_json_raises_error(self, invalid_json):
        with pytest.raises(json.JSONDecodeError):
            json_loader(invalid_json)
