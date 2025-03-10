from typing import Type
import pytest
from auto_archiver.core import Media
from auto_archiver.modules.s3_storage import S3Storage


class TestS3Storage:
    """
    Test suite for S3Storage.
    """

    module_name: str = "s3_storage"
    storage: Type[S3Storage]
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

    @pytest.fixture(autouse=True)
    def setup_storage(self, setup_module, mocker):
        self.s3 = S3Storage()
        self.storage = setup_module(self.module_name, self.config)

    def test_client_initialization(self):
        """Test that S3 client is initialized with correct parameters"""

        assert self.storage.s3 is not None
        assert self.storage.s3.meta.region_name == "test-region"

    def test_get_cdn_url_generation(self):
        """Test CDN URL formatting"""
        media = Media("test.txt")
        media.key = "path/to/file.txt"
        url = self.storage.get_cdn_url(media)
        assert url == "https://cdn.example.com/path/to/file.txt"
        media.key = "another/path.jpg"
        assert self.storage.get_cdn_url(media) == "https://cdn.example.com/another/path.jpg"

    def test_uploadf_sets_acl_public(self, mocker):
        media = Media("test.txt")
        mock_file = mocker.MagicMock()
        mock_s3_upload = mocker.patch.object(self.storage.s3, "upload_fileobj")
        mocker.patch.object(self.storage, "is_upload_needed", return_value=True)
        self.storage.uploadf(mock_file, media)
        mock_s3_upload.assert_called_once_with(
            mock_file,
            Bucket="test-bucket",
            Key=media.key,
            ExtraArgs={"ACL": "public-read", "ContentType": "text/plain"},
        )

    def test_upload_decision_logic(self, mocker):
        """Test is_upload_needed under different conditions"""
        media = Media("test.txt")
        assert self.storage.is_upload_needed(media) is True
        self.storage.random_no_duplicate = True
        mock_calc_hash = mocker.patch(
            "auto_archiver.modules.s3_storage.s3_storage.calculate_file_hash",
            return_value="beepboop123beepboop123beepboop123",
        )
        mock_file_in_folder = mocker.patch.object(self.storage, "file_in_folder", return_value="existing_key.txt")
        assert self.storage.is_upload_needed(media) is False
        assert media.key == "existing_key.txt"
        mock_file_in_folder.assert_called_with("no-dups/beepboop123beepboop123be")

    def test_skips_upload_when_duplicate_exists(self, mocker):
        """Test that upload skips when file_in_folder finds existing object"""
        self.storage.random_no_duplicate = True
        mock_file_in_folder = mocker.patch.object(
            S3Storage, "file_in_folder", return_value="existing_folder/existing_file.txt"
        )
        media = Media("test.txt")
        media.key = "original_path.txt"
        mock_calculate_hash = mocker.patch(
            "auto_archiver.modules.s3_storage.s3_storage.calculate_file_hash",
            return_value="beepboop123beepboop123beepboop123",
        )
        assert self.storage.is_upload_needed(media) is False
        assert media.key == "existing_folder/existing_file.txt"
        assert media.get("previously archived") is True
        mock_upload = mocker.patch.object(self.storage.s3, "upload_fileobj")
        result = self.storage.uploadf(None, media)
        mock_upload.assert_not_called()
        assert result is True

    def test_uploads_with_correct_parameters(self, mocker):
        media = Media("test.txt")
        media.key = "original_key.txt"
        mocker.patch.object(S3Storage, "is_upload_needed", return_value=True)
        media.mimetype = "image/png"
        mock_file = mocker.MagicMock()
        mock_upload = mocker.patch.object(self.storage.s3, "upload_fileobj")
        self.storage.uploadf(mock_file, media)
        mock_upload.assert_called_once_with(
            mock_file,
            Bucket="test-bucket",
            Key="original_key.txt",
            ExtraArgs={"ACL": "public-read", "ContentType": "image/png"},
        )

    def test_file_in_folder_exists(self, mocker):
        mock_list_objects = mocker.patch.object(
            self.storage.s3, "list_objects", return_value={"Contents": [{"Key": "path/to/file.txt"}]}
        )
        assert self.storage.file_in_folder("path/to/") == "path/to/file.txt"
