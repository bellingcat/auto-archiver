import boto3
from botocore.errorfactory import ClientError
from .base_storage import Storage
from dataclasses import dataclass
from loguru import logger


@dataclass
class S3Config:
    bucket: str
    region: str
    key: str
    secret: str
    folder: str = ""
    private: bool = False


class S3Storage(Storage):

    def __init__(self, config: S3Config):
        self.bucket = config.bucket
        self.region = config.region
        self.folder = self.clean_path(config.folder)
        self.private = config.private

        self.s3 = boto3.client(
            's3',
            region_name=self.region,
            endpoint_url=f'https://{self.region}.digitaloceanspaces.com',
            aws_access_key_id=config.key,
            aws_secret_access_key=config.secret
        )

    def _get_path(self, key):
        return self.folder + self.clean_path(self.subfolder) + key

    def get_cdn_url(self, key):
        return f'https://{self.bucket}.{self.region}.cdn.digitaloceanspaces.com/{self._get_path(key)}'

    def exists(self, key):
        try:
            self.s3.head_object(Bucket=self.bucket, Key=self._get_path(key))
            return True
        except ClientError:
            return False

    def uploadf(self, file, key, **kwargs):
        logger.debug(f'[S3 storage] uploading {file=}, {key=}')
        if self.private:
            extra_args = kwargs.get("extra_args", {})
        else:
            extra_args = kwargs.get("extra_args", {'ACL': 'public-read'})
        self.s3.upload_fileobj(file, Bucket=self.bucket, Key=self._get_path(key), ExtraArgs=extra_args)
