from typing import Type

import pytest

from auto_archiver.core.metadata import Metadata, Media
from auto_archiver.core.storage import Storage
from auto_archiver.core.module import ModuleFactory


class TestStorageBase(object):
    module_name: str = None
    config: dict = None

    @pytest.fixture(autouse=True)
    def setup_storage(self, setup_module):
        assert self.module_name is not None, "self.module_name must be set on the subclass"
        assert self.config is not None, "self.config must be a dict set on the subclass"
        self.storage: Type[Storage] = setup_module(self.module_name, self.config)


class TestBaseStorage(Storage):
    name = "test_storage"

    def get_cdn_url(self, media):
        return "cdn_url"

    def uploadf(self, file, key, **kwargs):
        return True


@pytest.fixture
def dummy_file(tmp_path):
    # create dummy.txt file
    dummy_file = tmp_path / "dummy.txt"
    dummy_file.write_text("test content")
    return str(dummy_file)


@pytest.fixture
def storage_base():
    def _storage_base(config):
        storage_base = TestBaseStorage()
        storage_base.config_setup({TestBaseStorage.name: config})
        storage_base.module_factory = ModuleFactory()
        return storage_base

    return _storage_base


@pytest.mark.parametrize(
    "path_generator, filename_generator, url, expected_key",
    [
        ("flat", "static", "https://example.com/file/", "folder/6ae8a75555209fd6c44157c0.txt"),
        ("flat", "random", "https://example.com/file/", "folder/pretend-random.txt"),
        ("url", "static", "https://example.com/file/", "folder/https-example-com-file/6ae8a75555209fd6c44157c0.txt"),
        ("url", "random", "https://example.com/file/", "folder/https-example-com-file/pretend-random.txt"),
        ("random", "static", "https://example.com/file/", "folder/pretend-random/6ae8a75555209fd6c44157c0.txt"),
        ("random", "random", "https://example.com/file/", "folder/pretend-random/pretend-random.txt"),
    ],
)
def test_storage_name_generation(
    storage_base, path_generator, filename_generator, url, expected_key, mocker, tmp_path, dummy_file
):
    mock_random = mocker.patch("auto_archiver.core.storage.random_str")
    mock_random.return_value = "pretend-random"

    config: dict = {
        "path_generator": path_generator,
        "filename_generator": filename_generator,
    }
    storage: Storage = storage_base(config)
    assert storage.path_generator == path_generator
    assert storage.filename_generator == filename_generator

    metadata = Metadata()
    metadata.set_context("folder", "folder")
    media = Media(filename=dummy_file)
    storage.set_key(media, url, metadata)
    print(media.key)
    assert media.key == expected_key


def test_really_long_name(storage_base, dummy_file):
    config: dict = {
        "path_generator": "url",
        "filename_generator": "static",
    }
    storage: Storage = storage_base(config)

    url = f"https://example.com/{'file' * 100}"
    media = Media(filename=dummy_file)
    storage.set_key(media, url, Metadata())
    assert media.key == f"https-example-com-{'file' * 13}/6ae8a75555209fd6c44157c0.txt"


def test_storage_loads_hash_enricher(storage_base, dummy_file):
    """Ensure 'hash_enricher' is properly loaded without an explicit import."""
    config = {"path_generator": "url", "filename_generator": "static"}
    storage = storage_base(config)

    url = "https://example.com/file/"
    media = Media(filename=dummy_file)
    metadata = Metadata()

    try:
        storage.set_key(media, url, metadata)
    except Exception as e:
        pytest.fail(f"Storage failed to dynamically load hash_enricher: {e}")

    assert media.key is not None, "Expected media.key to be set, but it was None"
