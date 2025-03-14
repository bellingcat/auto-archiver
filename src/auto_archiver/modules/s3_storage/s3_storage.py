from typing import IO

import boto3
import os
from loguru import logger

from auto_archiver.core import Media
from auto_archiver.core import Storage
from auto_archiver.utils.misc import calculate_file_hash, random_str

NO_DUPLICATES_FOLDER = "no-dups/"


class S3Storage(Storage):
    def setup(self) -> None:
        self.s3 = boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url.format(region=self.region),
            aws_access_key_id=self.key,
            aws_secret_access_key=self.secret,
        )
        if self.random_no_duplicate:
            logger.warning(
                "random_no_duplicate is set to True, this will override `path_generator`, `filename_generator` and `folder`."
            )

    def get_cdn_url(self, media: Media) -> str:
        return self.cdn_url.format(bucket=self.bucket, region=self.region, key=media.key)

    def uploadf(self, file: IO[bytes], media: Media, **kwargs: dict) -> None:
        if not self.is_upload_needed(media):
            return True

        extra_args = kwargs.get("extra_args", {})
        if not self.private and "ACL" not in extra_args:
            extra_args["ACL"] = "public-read"

        if "ContentType" not in extra_args:
            try:
                if media.mimetype:
                    extra_args["ContentType"] = media.mimetype
            except Exception as e:
                logger.warning(f"Unable to get mimetype for {media.key=}, error: {e}")
        self.s3.upload_fileobj(file, Bucket=self.bucket, Key=media.key, ExtraArgs=extra_args)
        return True

    def is_upload_needed(self, media: Media) -> bool:
        if self.random_no_duplicate:
            # checks if a folder with the hash already exists, if so it skips the upload
            hd = calculate_file_hash(media.filename)
            path = os.path.join(NO_DUPLICATES_FOLDER, hd[:24])

            if existing_key := self.file_in_folder(path):
                media._key = existing_key
                media.set("previously archived", True)
                logger.debug(f"skipping upload of {media.filename} because it already exists in {media.key}")
                return False

            _, ext = os.path.splitext(media.key)
            media._key = os.path.join(path, f"{random_str(24)}{ext}")
        return True

    def file_in_folder(self, path: str) -> str:
        # checks if path exists and is not an empty folder
        if not path.endswith("/"):
            path = path + "/"
        resp = self.s3.list_objects(Bucket=self.bucket, Prefix=path, Delimiter="/", MaxKeys=1)
        if "Contents" in resp:
            return resp["Contents"][0]["Key"]
        return False
