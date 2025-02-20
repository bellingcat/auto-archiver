from typing import Type
import pytest
from oauth2client import service_account

from auto_archiver.core import Media
from auto_archiver.modules.gdrive_storage import GDriveStorage
from auto_archiver.core.metadata import Metadata
from tests.storages.test_storage_base import TestStorageBase


@pytest.fixture
def gdrive_storage(setup_module, mocker):
    module_name: str = "gdrive_storage"
    storage: GDriveStorage
    config: dict = {'path_generator': 'url',
            'filename_generator': 'static',
            'root_folder_id': "fake_root_folder_id",
            'oauth_token': None,
            'service_account': 'fake_service_account.json'
                    }
    mocker.patch('google.oauth2.service_account.Credentials.from_service_account_file')
    return setup_module(module_name, config)


def test_initialize_fails_with_non_existent_creds(setup_module):
    """Test that the Google Drive service raises a FileNotFoundError when the service account file does not exist.
        (and isn't mocked)
    """
    config: dict = {'path_generator': 'url',
                    'filename_generator': 'static',
                    'root_folder_id': "fake_root_folder_id",
                    'oauth_token': None,
                    'service_account': 'fake_service_account.json'
                    }
    with pytest.raises(FileNotFoundError) as exc_info:
        setup_module("gdrive_storage", config)
    assert "No such file or directory" in str(exc_info.value)


def test_get_id_from_parent_and_name(gdrive_storage, mocker):
    """Test _get_id_from_parent_and_name returns correct id from an API result."""
    fake_list = mocker.MagicMock()
    fake_list.execute.return_value = {"files": [{"id": "123", "name": "testname"}]}
    fake_service = mocker.MagicMock()
    # mock the files.list return value
    fake_service.files.return_value.list.return_value = fake_list
    gdrive_storage.service = fake_service
    result = gdrive_storage._get_id_from_parent_and_name("parent", "mock", retries=1, use_mime_type=False)
    assert result == "123"

def test_path_parts():
    media = Media(filename="test.jpg")
    media.key = "folder1/folder2/test.jpg"



@pytest.mark.skip(reason="Requires real credentials")
@pytest.mark.download
class TestGDriveStorageConnected(TestStorageBase):
    """
    'Real' tests for GDriveStorage.
    """

    module_name: str = "gdrive_storage"
    storage: Type[GDriveStorage]
    config: dict = {'path_generator': 'url',
            'filename_generator': 'static',
            # TODO: replace with real root folder id
            'root_folder_id': "1TVY_oJt95_dmRSEdP9m5zFy7l50TeCSk",
            'oauth_token': None,
            'service_account': 'secrets/service_account.json'
                    }


    def test_initialize_with_real_credentials(self):
        """
        Test that the Google Drive service can be initialized with real credentials.
        """
        assert self.storage.service is not None


