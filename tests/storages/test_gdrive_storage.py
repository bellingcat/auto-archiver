from typing import Type
import pytest
from unittest.mock import MagicMock, patch
from auto_archiver.core import Media
from auto_archiver.modules.gdrive_storage import GDriveStorage
from auto_archiver.core.metadata import Metadata
from tests.storages.test_storage_base import TestStorageBase


class TestGDriveStorage(TestStorageBase):
    """
    Test suite for GDriveStorage.
    """

    module_name: str = "gdrive_storage"
    storage: Type[GDriveStorage]
    config: dict = {'path_generator': 'url',
            'filename_generator': 'static',
            'root_folder_id': "fake_root_folder_id",
            'oauth_token': None,
            'service_account': 'fake_service_account.json'
                    }


    def test_initialize_fails_with_non_existent_creds(self):
        """
        Test that the Google Drive service raises a FileNotFoundError when the service account file does not exist.
        """
        # Act and Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            self.storage.setup(self.config)
        assert "No such file or directory" in str(exc_info.value)

    def test_path_parts(self):
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


