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

    @pytest.mark.skip(reason="Requires real credentials")
    @pytest.mark.download
    def test_initialize_with_real_credentials(self):
        """
        Test that the Google Drive service can be initialized with real credentials.
        """
        self.storage.service_account = 'secrets/service_account.json'  # Path to real credentials
        self.storage.initialise()
        assert self.storage.service is not None


    def test_initialize_fails_with_non_existent_creds(self):
        """
        Test that the Google Drive service raises a FileNotFoundError when the service account file does not exist.
        """
        # Act and Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            self.storage.initialise()
        assert "No such file or directory" in str(exc_info.value)

