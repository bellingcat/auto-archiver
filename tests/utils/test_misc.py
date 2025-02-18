import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from auto_archiver.utils.misc import (
    mkdir_if_not_exists,
    expand_url,
    getattr_or,
    DateTimeEncoder,
    dump_payload,
    get_datetime_from_str,
    update_nested_dict,
    calculate_file_hash,
    random_str,
    get_timestamp
)


@pytest.fixture
def sample_file(tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")
    return file_path


class TestDirectoryUtils:
    def test_mkdir_creates_new_directory(self, tmp_path):
        new_dir = tmp_path / "new_folder"
        mkdir_if_not_exists(new_dir)
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_mkdir_exists_quietly(self, tmp_path):
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        mkdir_if_not_exists(existing_dir)
        assert existing_dir.exists()

class TestURLExpansion:
    @pytest.mark.parametrize("input_url,expected", [
        ("https://example.com", "https://example.com"),
        ("https://t.co/test", "https://expanded.url")
    ])
    def test_expand_url(self, input_url, expected):
        mock_response = Mock()
        mock_response.url = "https://expanded.url"
        with patch('requests.get', return_value=mock_response):

            result = expand_url(input_url)
            assert result == expected

    def test_expand_url_handles_errors(self, caplog):
        with patch('requests.get', side_effect=Exception("Connection error")):
            url = "https://t.co/error"
            result = expand_url(url)
            assert result == url
            assert f"Failed to expand url {url}" in caplog.text

class TestAttributeHandling:
    class Sample:
        exists = "value"
        none = None

    @pytest.mark.parametrize("obj,attr,default,expected", [
        (Sample(), "exists", "default", "value"),
        (Sample(), "none", "default", "default"),
        (Sample(), "missing", "default", "default"),
        (None, "anything", "fallback", "fallback"),
    ])
    def test_getattr_or(self, obj, attr, default, expected):
        # Test gets attribute or returns a default value
        assert getattr_or(obj, attr, default) == expected

class TestDateTimeHandling:
    def test_datetime_encoder(self, sample_datetime):
        result = json.dumps({"dt": sample_datetime}, cls=DateTimeEncoder)
        loaded = json.loads(result)
        assert loaded["dt"] == str(sample_datetime)

    def test_dump_payload(self, sample_datetime):
        payload = {"timestamp": sample_datetime}
        result = dump_payload(payload)
        assert str(sample_datetime) in result

    @pytest.mark.parametrize("dt_str,fmt,expected", [
        ("2023-01-01 12:00:00+00:00", None, datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)),
        ("20230101 120000", "%Y%m%d %H%M%S", datetime(2023, 1, 1, 12, 0)),
        ("invalid", None, None),
    ])
    def test_datetime_from_string(self, dt_str, fmt, expected):
        result = get_datetime_from_str(dt_str, fmt)
        if expected is None:
            assert result is None
        else:
            assert result == expected.replace(tzinfo=result.tzinfo)

class TestDictUtils:
    @pytest.mark.parametrize("original,update,expected", [
        ({"a": 1}, {"b": 2}, {"a": 1, "b": 2}),
        ({"nested": {"a": 1}}, {"nested": {"b": 2}}, {"nested": {"a": 1, "b": 2}}),
        ({"a": {"b": {"c": 1}}}, {"a": {"b": {"c": 2}}}, {"a": {"b": {"c": 2}}}),
    ])
    def test_update_nested_dict(self, original, update, expected):
        update_nested_dict(original, update)
        assert original == expected

class TestHashingUtils:
    def test_file_hashing(self, sample_file):
        expected = hashlib.sha256(b"test content").hexdigest()
        assert calculate_file_hash(str(sample_file)) == expected

    def test_large_file_hashing(self, tmp_path):
        file_path = tmp_path / "large.bin"
        content = b"0" * 16_000_000 * 2  # 32MB
        file_path.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()
        assert calculate_file_hash(str(file_path)) == expected

class TestMiscUtils:
    def test_random_str_length(self):
        for length in [8, 16, 32]:
            assert len(random_str(length)) == length

    def test_random_str_raises_too_long(self):
        with pytest.raises(AssertionError) as exc_info:
            random_str(64)
            assert "length must be less than 32 as UUID4 is used" == str(exc_info.value)

    def test_random_str_uniqueness(self):
        assert random_str() != random_str()

    @pytest.mark.parametrize("ts_input,utc,iso,expected_type", [
        (datetime.now(), True, True, str),
        ("2023-01-01T12:00:00+00:00", False, False, datetime),
        (1672574400, True, True, str),
    ])
    def test_timestamp_parsing(self, ts_input, utc, iso, expected_type):
        result = get_timestamp(ts_input, utc=utc, iso=iso)
        assert isinstance(result, expected_type)

    def test_invalid_timestamp_returns_none(self):
        assert get_timestamp("invalid-date") is None