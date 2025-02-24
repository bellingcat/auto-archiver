import os
import hashlib
import pytest
from auto_archiver.core import Media, Metadata
from auto_archiver.modules.atlos_storage import AtlosStorage


class FakeAPIResponse:
    """Simulate a response object."""

    def __init__(self, data: dict, raise_error: bool = False) -> None:
        self._data = data
        self.raise_error = raise_error

    def json(self) -> dict:
        return self._data

    def raise_for_status(self) -> None:
        if self.raise_error:
            raise Exception("HTTP error")


@pytest.fixture
def atlos_storage(setup_module) -> AtlosStorage:
    """Fixture for AtlosStorage."""
    configs: dict = {
        "api_token": "abc123",
        "atlos_url": "https://platform.atlos.org",
    }
    return setup_module("atlos_storage", configs)


@pytest.fixture
def media(tmp_path) -> Media:
    """Fixture for Media."""
    content = b"media content"
    file_path = tmp_path / "media.txt"
    file_path.write_bytes(content)
    media = Media(filename=str(file_path))
    media.properties = {"something": "Title"}
    media.key = "key"
    return media


def test_get_cdn_url(atlos_storage: AtlosStorage) -> None:
    """Test get_cdn_url returns the configured atlos_url."""
    media = Media(filename="dummy.mp4")
    url = atlos_storage.get_cdn_url(media)
    assert url == atlos_storage.atlos_url


def test_hash(tmp_path, atlos_storage: AtlosStorage) -> None:
    """Test _hash() computes the correct SHA-256 hash of a file."""
    content = b"hello world"
    file_path = tmp_path / "test.txt"
    file_path.write_bytes(content)
    media = Media(filename="dummy.mp4")
    media.filename = str(file_path)
    expected_hash = hashlib.sha256(content).hexdigest()
    assert atlos_storage._hash(media) == expected_hash


def test_upload_no_atlos_id(tmp_path, atlos_storage: AtlosStorage, media: Media, mocker) -> None:
    """Test upload() returns False when metadata lacks atlos_id."""
    metadata = Metadata()  # atlos_id not set
    post_mock = mocker.patch("requests.post")
    result = atlos_storage.upload(media, metadata)
    assert result is False
    post_mock.assert_not_called()


def test_upload_already_uploaded(atlos_storage: AtlosStorage,
                                 metadata: Metadata,
                                 media: Media,
                                 tmp_path,
                                 mocker) -> None:
    """Test upload() returns True if media hash already exists."""
    content = b"media content"
    metadata.set("atlos_id", 101)
    media_hash = hashlib.sha256(content).hexdigest()
    fake_get = FakeAPIResponse({
        "result": {"artifacts": [{"file_hash_sha256": media_hash}]}
    })
    get_mock = mocker.patch("requests.get", return_value=fake_get)
    post_mock = mocker.patch("requests.post")
    result = atlos_storage.upload(media, metadata)
    assert result is True
    get_mock.assert_called_once()
    post_mock.assert_not_called()


def test_upload_not_uploaded(tmp_path, atlos_storage: AtlosStorage,
                             metadata: Metadata,
                             media: Media,
                             mocker) -> None:
    """Test upload() uploads media when not already present."""
    metadata.set("atlos_id", 202)
    fake_get = FakeAPIResponse({
        "result": {"artifacts": [{"file_hash_sha256": "different_hash"}]}
    })
    get_mock = mocker.patch("requests.get", return_value=fake_get)
    fake_post = FakeAPIResponse({}, raise_error=False)
    post_mock = mocker.patch("requests.post", return_value=fake_post)
    result = atlos_storage.upload(media, metadata)
    assert result is True
    get_mock.assert_called_once()
    post_mock.assert_called_once()
    expected_url = f"{atlos_storage.atlos_url}/api/v2/source_material/upload/202"
    expected_headers = {"Authorization": f"Bearer {atlos_storage.api_token}"}
    expected_params = {"title": media.properties}
    call_kwargs = post_mock.call_args.kwargs
    assert call_kwargs["headers"] == expected_headers
    assert call_kwargs["params"] == expected_params
    # Verify the URL passed to requests.post.
    posted_url = call_kwargs.get("url") or post_mock.call_args.args[0]
    assert posted_url == expected_url
    # Verify files parameter contains the correct filename.
    file_tuple = call_kwargs["files"]["file"]
    assert file_tuple[0] == os.path.basename(media.filename)


def test_upload_post_http_error(tmp_path,
                                atlos_storage: AtlosStorage,
                                metadata: Metadata,
                                media: Media,
                                mocker) -> None:
    """Test upload() propagates HTTP error during POST."""
    metadata.set("atlos_id", 303)
    fake_get = FakeAPIResponse({
        "result": {"artifacts": []}
    })
    mocker.patch("requests.get", return_value=fake_get)
    fake_post = FakeAPIResponse({}, raise_error=True)
    mocker.patch("requests.post", return_value=fake_post)
    with pytest.raises(Exception, match="HTTP error"):
        atlos_storage.upload(media, metadata)


def test_uploadf_not_implemented(atlos_storage: AtlosStorage) -> None:
    """Test uploadf() returns None (not implemented)."""
    result = atlos_storage.uploadf(None, "dummy")
    assert result is None
