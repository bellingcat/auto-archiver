from typing import Type
import pytest
from unittest.mock import MagicMock, patch
from auto_archiver.core import Media
from auto_archiver.modules.hash_enricher import HashEnricher
from auto_archiver.modules.s3_storage import s3_storage


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

    def test_client_initialization(self):
        """Test that S3 client is initialized with correct parameters"""
        assert self.storage.s3 is not None
        assert self.storage.s3.meta.region_name == 'test-region'

    def test_get_cdn_url_generation(self):
        """Test CDN URL formatting """
        media = Media("test.txt")
        media.key = "path/to/file.txt"
        url = self.storage.get_cdn_url(media)
        assert url == "https://cdn.example.com/path/to/file.txt"
        media.key = "another/path.jpg"
        assert self.storage.get_cdn_url(media) == "https://cdn.example.com/another/path.jpg"

    def test_uploadf_sets_acl_public(self):
        media = Media("test.txt")
        mock_file = MagicMock()
        with patch.object(self.storage.s3, 'upload_fileobj') as mock_s3_upload,  \
            patch.object(self.storage, 'is_upload_needed', return_value=True):
            self.storage.uploadf(mock_file, media)
            mock_s3_upload.assert_called_once_with(
                mock_file,
                Bucket='test-bucket',
                Key=media.key,
                ExtraArgs={'ACL': 'public-read', 'ContentType': 'text/plain'}
            )

    def test_upload_decision_logic(self):
        """Test is_upload_needed under different conditions"""
        media = Media("test.txt")
        # Test default state (random_no_duplicate=False)
        assert self.storage.is_upload_needed(media) is True
        # Set duplicate checking config to true:

        self.storage.random_no_duplicate = True
        with patch('auto_archiver.modules.hash_enricher.HashEnricher.calculate_hash') as mock_calc_hash, \
                patch.object(self.storage, 'file_in_folder') as mock_file_in_folder:
            mock_calc_hash.return_value = 'beepboop123beepboop123beepboop123'
            mock_file_in_folder.return_value = 'existing_key.txt'
            # Test duplicate result
            assert self.storage.is_upload_needed(media) is False
            assert media.key == 'existing_key.txt'
            mock_file_in_folder.assert_called_with(
                # (first 24 chars of hash)
                'no-dups/beepboop123beepboop123be'
            )


    @patch.object(s3_storage.S3Storage, 'file_in_folder')
    def test_skips_upload_when_duplicate_exists(self, mock_file_in_folder):
        """Test that upload skips when file_in_folder finds existing object"""
        self.storage.random_no_duplicate = True
        mock_file_in_folder.return_value = "existing_folder/existing_file.txt"
        # Create test media with calculated hash
        media = Media("test.txt")
        media.key = "original_path.txt"

        with patch('auto_archiver.modules.hash_enricher.HashEnricher.calculate_hash') as mock_calculate_hash:
            mock_calculate_hash.return_value = "beepboop123beepboop123beepboop123"
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
        media.key = "original_key.txt"
        mock_upload_needed.return_value = True
        media.mimetype = 'image/png'
        mock_file = MagicMock()

        with patch.object(self.storage.s3, 'upload_fileobj') as mock_upload:
            self.storage.uploadf(mock_file, media)
            # verify call occured with these params
            mock_upload.assert_called_once_with(
                mock_file,
                Bucket='test-bucket',
                Key='original_key.txt',
                ExtraArgs={
                    'ACL': 'public-read',
                    'ContentType': 'image/png'
                }
            )

    def test_file_in_folder_exists(self):
        with patch.object(self.storage.s3, 'list_objects') as mock_list_objects:
            mock_list_objects.return_value = {'Contents': [{'Key': 'path/to/file.txt'}]}
            assert self.storage.file_in_folder('path/to/') == 'path/to/file.txt'