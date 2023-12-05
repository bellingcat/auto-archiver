
from typing import IO
import boto3, os

from ..utils.misc import random_str
from ..core import Media
from ..storages import Storage
from ..enrichers import HashEnricher
from loguru import logger

NO_DUPLICATES_FOLDER = "no-dups/"
class S3Storage(Storage):
    name = "s3_storage"

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.s3 = boto3.client(
            's3',
            region_name=self.region,
            endpoint_url=self.endpoint_url.format(region=self.region),
            aws_access_key_id=self.key,
            aws_secret_access_key=self.secret
        )
        self.random_no_duplicate = bool(self.random_no_duplicate)
        if self.random_no_duplicate:
            logger.warning("random_no_duplicate is set to True, this will override `path_generator`, `filename_generator` and `folder`.")

    @staticmethod
    def configs() -> dict:
        return dict(
            Storage.configs(),
            ** {
                "bucket": {"default": None, "help": "S3 bucket name"},
                "region": {"default": None, "help": "S3 region name"},
                "key": {"default": None, "help": "S3 API key"},
                "secret": {"default": None, "help": "S3 API secret"},
                "random_no_duplicate": {"default": False, "help": f"if set, it will override `path_generator`, `filename_generator` and `folder`. It will check if the file already exists and if so it will not upload it again. Creates a new root folder path `{NO_DUPLICATES_FOLDER}`"},
                "endpoint_url": {
                    "default": 'https://{region}.digitaloceanspaces.com',
                    "help": "S3 bucket endpoint, {region} are inserted at runtime"
                },
                "cdn_url": {
                    "default": 'https://{bucket}.{region}.cdn.digitaloceanspaces.com/{key}',
                    "help": "S3 CDN url, {bucket}, {region} and {key} are inserted at runtime"
                },
                "private": {"default": False, "help": "if true S3 files will not be readable online"},
            })

    def get_cdn_url(self, media: Media) -> str:
        return self.cdn_url.format(bucket=self.bucket, region=self.region, key=media.key)

    def uploadf(self, file: IO[bytes], media: Media, **kwargs: dict) -> None:
        if not self.is_upload_needed(media): return True

        if self.random_no_duplicate:
            # checks if a folder with the hash already exists, if so it skips the upload
            he = HashEnricher({"hash_enricher": {"algorithm": "SHA-256", "chunksize": 1.6e7}})
            hd = he.calculate_hash(media.filename)
            path = os.path.join(NO_DUPLICATES_FOLDER, hd[:24])

            if existing_key:=self.file_in_folder(path):
                media.key = existing_key
                logger.debug(f"skipping upload of {media.filename} because it already exists in {media.key}")
                return True
            
            _, ext = os.path.splitext(media.key)
            media.key = os.path.join(path, f"{random_str(24)}{ext}")

        extra_args = kwargs.get("extra_args", {})
        if not self.private and 'ACL' not in extra_args:
            extra_args['ACL'] = 'public-read'

        if 'ContentType' not in extra_args:
            try:
                if media.mimetype:
                    extra_args['ContentType'] = media.mimetype
            except Exception as e:
                logger.warning(f"Unable to get mimetype for {media.key=}, error: {e}")

        self.s3.upload_fileobj(file, Bucket=self.bucket, Key=media.key, ExtraArgs=extra_args)
        return True
    
    def is_upload_needed(self, media: Media) -> bool:
        if self.random_no_duplicate:
            # checks if a folder with the hash already exists, if so it skips the upload
            he = HashEnricher({"hash_enricher": {"algorithm": "SHA-256", "chunksize": 1.6e7}})
            hd = he.calculate_hash(media.filename)
            path = os.path.join(NO_DUPLICATES_FOLDER, hd[:24])

            if existing_key:=self.file_in_folder(path):
                media.key = existing_key
                logger.debug(f"skipping upload of {media.filename} because it already exists in {media.key}")
                return False
            
            _, ext = os.path.splitext(media.key)
            media.key = os.path.join(path, f"{random_str(24)}{ext}")
        return True
    
    
    def file_in_folder(self, path:str) -> str:
        # checks if path exists and is not an empty folder
        if not path.endswith('/'):
            path = path + '/' 
        resp = self.s3.list_objects(Bucket=self.bucket, Prefix=path, Delimiter='/', MaxKeys=1)
        if 'Contents' in resp:
            return resp['Contents'][0]['Key']
        return False

