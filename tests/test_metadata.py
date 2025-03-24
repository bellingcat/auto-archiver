import pytest
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any
from auto_archiver.core.metadata import Metadata


@pytest.fixture
def basic_metadata():
    m = Metadata()
    m.set_url("https://example.com")
    m.set("title", "Test Page")
    return m


@dataclass
class MockMedia:
    filename: str = ""
    mimetype: str = ""
    data: dict = None

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default) if self.data else default

    def set(self, key: str, value: Any) -> None:
        if not self.data:
            self.data = {}
        self.data[key] = value


@pytest.fixture
def media_file():
    def _create(filename="test.txt", mimetype="text/plain", hash_value=None):
        m = MockMedia(filename=filename, mimetype=mimetype)
        if hash_value:
            m.set("hash", hash_value)
        return m

    return _create


def test_initial_state():
    m = Metadata()
    assert m.status == "no archiver"
    assert m.metadata == {"_processed_at": m.get("_processed_at")}
    assert m.media == []
    assert isinstance(m.get("_processed_at"), datetime)


def test_url_properties(basic_metadata):
    assert basic_metadata.get_url() == "https://example.com"
    assert basic_metadata.netloc == "example.com"


def test_simple_merge(basic_metadata):
    right = Metadata(status="success")
    right.set("title", "Test Title")

    basic_metadata.merge(right)
    assert basic_metadata.status == "success"
    assert basic_metadata.get("title") == "Test Title"


def test_left_merge():
    left = Metadata().set("tags", ["a"]).set("stats", {"views": 10}).set("status", "success")
    right = Metadata().set("tags", ["b"]).set("stats", {"likes": 5}).set("status", "no archiver")

    left.merge(right, overwrite_left=True)
    assert left.get("status") == "no archiver"
    assert left.get("tags") == ["a", "b"]
    assert left.get("stats") == {"views": 10, "likes": 5}


def test_media_management(basic_metadata, media_file):
    media1 = media_file(hash_value="abc")
    media2 = media_file(hash_value="abc")  # Duplicate
    media3 = media_file(hash_value="def")

    basic_metadata.add_media(media1, "m1")
    basic_metadata.add_media(media2, "m2")
    basic_metadata.add_media(media3)

    assert len(basic_metadata.media) == 3
    basic_metadata.remove_duplicate_media_by_hash()
    assert len(basic_metadata.media) == 2
    assert basic_metadata.get_media_by_id("m1") == media1


def test_success():
    m = Metadata()
    assert not m.is_success()
    m.success("context")
    assert m.is_success()
    assert m.status == "context: success"


def test_is_empty():
    m = Metadata()
    assert m.is_empty()
    # meaningless ids
    (
        m.set("url", "example.com")
        .set("total_bytes", 100)
        .set("archive_duration_seconds", 10)
        .set("_processed_at", datetime.now(timezone.utc))
    )
    assert m.is_empty()


def test_store():
    pass


# Test Media operations


# Test custom getter/setters


def test_get_set_url():
    m = Metadata()
    m.set_url("http://example.com")
    assert m.get_url() == "http://example.com"
    with pytest.raises(AssertionError):
        m.set_url("")
    assert m.get("url") == "http://example.com"


def test_set_content():
    m = Metadata()
    m.set_content("Some content")
    assert m.get("content") == "Some content"
    # Test appending
    m.set_content("New content")
    # Do we want to add a line break to the method?
    assert m.get("content") == "Some contentNew content"


def test_choose_most_complex():
    pass


def test_get_context():
    m = Metadata()
    m.set_context("somekey", "somevalue")
    assert m.get_context("somekey") == "somevalue"
    assert m.get_context("nonexistent") is None
    m.set_context("anotherkey", "anothervalue")
    # check the previous is retained
    assert m.get_context("somekey") == "somevalue"
    assert m.get_context("anotherkey") == "anothervalue"
    assert len(m._context) == 2


def test_choose_most_complete():
    m_more = Metadata()
    m_more.set_title("Title 1")
    m_more.set_content("Content 1")
    m_more.set_url("https://example.com")

    m_less = Metadata()
    m_less.set_title("Title 2")
    m_less.set_content("Content 2")
    m_less.set_url("https://example.com")
    m_less.set_context("key", "value")

    res = Metadata.choose_most_complete([m_more, m_less])
    assert res.metadata.get("title") == "Title 1"


def test_choose_most_complete_from_pickles(unpickle):
    # test most complete from pickles before and after an enricher has run
    # Only compares length of media, not the actual media
    m_before_enriching = unpickle("metadata_enricher_ytshort_input.pickle")
    m_after_enriching = unpickle("metadata_enricher_ytshort_expected.pickle")
    # Iterates `for r in results[1:]:`
    res = Metadata.choose_most_complete([Metadata(), m_after_enriching, m_before_enriching])
    assert res.media == m_after_enriching.media
