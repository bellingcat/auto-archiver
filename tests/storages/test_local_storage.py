import os
from pathlib import Path

import pytest

from auto_archiver.core import Media, Metadata
from auto_archiver.modules.local_storage import LocalStorage
from auto_archiver.core.consts import SetupError


@pytest.fixture
def local_storage(setup_module, tmp_path) -> LocalStorage:
    save_to = tmp_path / "local_archive"
    save_to.mkdir()
    configs: dict = {
        "path_generator": "flat",
        "filename_generator": "static",
        "save_to": str(save_to),
        "save_absolute": False,
    }
    return setup_module("local_storage", configs)


@pytest.fixture
def sample_media(tmp_path) -> Media:
    """Fixture creating a Media object with temporary source file"""
    src_file = tmp_path / "source.txt"
    src_file.write_text("test content")
    return Media(filename=str(src_file))


def test_too_long_save_path(setup_module):
    with pytest.raises(SetupError):
        setup_module("local_storage", {"save_to": "long" * 100})


def test_get_cdn_url_relative(local_storage):
    local_storage.filename_generator = "random"
    media = Media(filename="dummy.txt")
    local_storage.set_key(media, "https://example.com", Metadata())
    expected = os.path.join(local_storage.save_to, media.key)
    assert local_storage.get_cdn_url(media) == expected


def test_get_cdn_url_absolute(local_storage):
    local_storage.filename_generator = "random"

    media = Media(filename="dummy.txt")
    local_storage.save_absolute = True
    local_storage.set_key(media, "https://example.com", Metadata())
    expected = os.path.abspath(os.path.join(local_storage.save_to, media.key))
    assert local_storage.get_cdn_url(media) == expected


def test_upload_file_contents_and_metadata(local_storage, sample_media):
    local_storage.store(sample_media, "https://example.com", Metadata())
    dest = os.path.join(local_storage.save_to, sample_media.key)
    assert Path(sample_media.filename).read_text() == Path(dest).read_text()


def test_upload_nonexistent_source(local_storage):
    media = Media(_key="missing.txt", filename="nonexistent.txt")
    with pytest.raises(FileNotFoundError):
        local_storage.upload(media)
