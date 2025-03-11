
import os
from pathlib import Path

import pytest

from auto_archiver.core import Media
from auto_archiver.modules.local_storage import LocalStorage


@pytest.fixture
def local_storage(setup_module) -> LocalStorage:
    configs: dict = {
        "path_generator": "flat",
        "filename_generator": "static",
        "save_to": "./local_archive",
        "save_absolute": False,
    }
    return setup_module("local_storage", configs)

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


