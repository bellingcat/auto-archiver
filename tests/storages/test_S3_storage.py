from typing import Type
import pytest
from unittest.mock import MagicMock, patch, mock_open
from auto_archiver.core import Media
from auto_archiver.modules.s3_storage import s3_storage
from tests.storages.test_storage_base import TestStorageBase


class TestGDriveStorage:
    """
    Test suite for GDriveStorage.
    """
    module_name: str = "s3_storage"
    storage: Type[s3_storage]
    s3: MagicMock
    config: dict = {
        "path_generator": "flat",
        "filename_generator": "static",
        "bucket": "test-bucket",
        "region": "test-region",
        "key": "test-key",
        "secret": "test-secret",
        "random_no_duplicate": False,
        "endpoint_url": "https://{region}.example.com",
        "cdn_url": "https://cdn.example.com/{key}",
        "private": False,
    }

    @patch('boto3.client')
    @pytest.fixture(autouse=True)
    def setup_storage(self, setup_module):
        self.storage = setup_module(self.module_name, self.config)
        self.storage.initialise()

    @patch('boto3.client')
    def test_client_initialization(self, mock_boto_client, setup_module):
        """Test that S3 client is initialized with correct parameters"""
        self.storage.initialise()
        mock_boto_client.assert_called_once_with(
            's3',
            region_name='test-region',
            endpoint_url='https://test-region.example.com',
            aws_access_key_id='test-key',
            aws_secret_access_key='test-secret'
        )

    def test_get_cdn_url_generation(self):
        """Test CDN URL formatting """
        media = Media("test.txt")
        media.key = "path/to/file.txt"
        url = self.storage.get_cdn_url(media)
        assert url == "https://cdn.example.com/path/to/file.txt"
        media.key = "another/path.jpg"
        assert self.storage.get_cdn_url(media) == "https://cdn.example.com/another/path.jpg"


    @patch.object(s3_storage.S3Storage, 'file_in_folder')
    def test_skips_upload_when_duplicate_exists(self, mock_file_in_folder):
        """Test that upload skips when file_in_folder finds existing object"""
        # Setup test-specific configuration
        self.storage.random_no_duplicate = True
        mock_file_in_folder.return_value = "existing_folder/existing_file.txt"
        # Create test media with calculated hash
        media = Media("test.txt")
        media.key = "original_path.txt"

        # Mock hash calculation
        with patch.object(self.storage, 'calculate_hash') as mock_calculate_hash:
            mock_calculate_hash.return_value = "testhash123"
            # Verify upload
            assert self.storage.is_upload_needed(media) is False
            assert media.key == "existing_folder/existing_file.txt"
            assert media.get("previously archived") is True

            with patch.object(self.storage.s3, 'upload_fileobj') as mock_upload:
                result = self.storage.uploadf(None, media)
                mock_upload.assert_not_called()
                assert result is True

    @patch.object(s3_storage.S3Storage, 'is_upload_needed')
    def test_uploads_with_correct_parameters(self, mock_upload_needed):
        media = Media("test.txt")
        mock_upload_needed.return_value = True
        media.mimetype = 'image/png'
        mock_file = MagicMock()

        with patch.object(self.storage.s3, 'upload_fileobj') as mock_upload:
            self.storage.uploadf(mock_file, media)

            # Verify core upload parameters
            mock_upload.assert_called_once_with(
                mock_file,
                Bucket='test-bucket',
                # Key='original_key.txt',
                Key=None,
                ExtraArgs={
                    'ACL': 'public-read',
                    'ContentType': 'image/png'
                }
            )