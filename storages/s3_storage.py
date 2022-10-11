import uuid, os, mimetypes
from dataclasses import dataclass

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
    endpoint_url: str = "https://{region}.digitaloceanspaces.com"
    cdn_url: str = "https://{bucket}.{region}.cdn.digitaloceanspaces.com/{key}"
    private: bool = False
    key_path: str = "default"  # 'default' uses full naming, 'random' uses generated uuid


class S3Storage(Storage):

    def __init__(self, config: S3Config):
        self.bucket = config.bucket
        self.region = config.region
        self.folder = config.folder
        self.private = config.private
        self.cdn_url = config.cdn_url
        self.key_path = config.key_path
        self.key_dict = {}

        self.s3 = boto3.client(
            's3',
            region_name=config.region,
            endpoint_url=config.endpoint_url.format(region=config.region),
            aws_access_key_id=config.key,
            aws_secret_access_key=config.secret
        )

    def _get_path(self, key):
        """
        Depends on the self.key_path configuration:
        * random - assigns a random UUID which can be used in conjunction with "private=false" to have unguessable documents publicly available -> self.folder/randomUUID
        * default -> defaults to self.folder/key
        """
        # defaults to /key
        final_key = key
        if self.key_path == "random":
            if key not in self.key_dict:
                ext = os.path.splitext(key)[1]
                self.key_dict[key] = f"{str(uuid.uuid4())}{ext}"
            final_key = self.key_dict[key]
        return os.path.join(self.folder, final_key)

    def get_cdn_url(self, key):
        return self.cdn_url.format(bucket=self.bucket, region=self.region, key=self._get_path(key))

    def exists(self, key):
        try:
            self.s3.head_object(Bucket=self.bucket, Key=self._get_path(key))
            return True
        except ClientError:
            return False

    def uploadf(self, file, key, **kwargs):
        if self.private:
            extra_args = kwargs.get("extra_args", {})
        else:
            extra_args = kwargs.get("extra_args", {'ACL': 'public-read'})
        if key.endswith('.wacz'):
            extra_args['ContentType'] = "application/zip"
        else:
            extra_args['ContentType'] = mimetypes.guess_type(key)[0]

        self.s3.upload_fileobj(file, Bucket=self.bucket, Key=self._get_path(key), ExtraArgs=extra_args)
