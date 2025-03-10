import os
from pathlib import Path

import pytest

from auto_archiver.core import Media
from auto_archiver.modules.local_storage import LocalStorage


@pytest.fixture
def local_storage(setup_module, tmp_path) -> LocalStorage:
    save_to = tmp_path / "local_archive"
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
    return Media(key="subdir/test.txt", filename=str(src_file))


def test_get_cdn_url_relative(local_storage):
    media = Media(key="test.txt", filename="dummy.txt")
    expected = os.path.join(local_storage.save_to, media.key)
    assert local_storage.get_cdn_url(media) == expected


def test_get_cdn_url_absolute(local_storage):
    media = Media(key="test.txt", filename="dummy.txt")
    local_storage.save_absolute = True
    expected = os.path.abspath(os.path.join(local_storage.save_to, media.key))
    assert local_storage.get_cdn_url(media) == expected


def test_upload_file_contents_and_metadata(local_storage, sample_media):
    dest = os.path.join(local_storage.save_to, sample_media.key)
    assert local_storage.upload(sample_media) is True
    assert Path(sample_media.filename).read_text() == Path(dest).read_text()


def test_upload_nonexistent_source(local_storage):
    media = Media(key="missing.txt", filename="nonexistent.txt")
    with pytest.raises(FileNotFoundError):
        local_storage.upload(media)
