import os
from typing import IO, List, Optional
from loguru import logger
import requests
import hashlib

from ..core import Media, Metadata
from ..storages import Storage
from ..utils import get_atlos_config_options


class AtlosStorage(Storage):
    name = "atlos_storage"

    def __init__(self, config: dict) -> None:
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return dict(Storage.configs(), **get_atlos_config_options())

    def get_cdn_url(self, _media: Media) -> str:
        # It's not always possible to provide an exact URL, because it's
        # possible that the media once uploaded could have been copied to
        # another project.
        return self.atlos_url
    
    def _hash(self, media: Media) -> str:
        # Hash the media file using sha-256. We don't use the existing auto archiver
        # hash because there's no guarantee that the configuerer is using sha-256, which
        # is how Atlos hashes files.

        sha256 = hashlib.sha256()
        with open(media.filename, "rb") as f:
            while True:
                buf = f.read(4096)
                if not buf: break
                sha256.update(buf)
        return sha256.hexdigest()

    def upload(self, media: Media, metadata: Optional[Metadata]=None, **_kwargs) -> bool:
        atlos_id = metadata.get("atlos_id")
        if atlos_id is None:
            logger.error(f"No Atlos ID found in metadata; can't store {media.filename} on Atlos")
            return False
        
        media_hash = self._hash(media)
        
        # Check whether the media has already been uploaded
        source_material = requests.get(
            f"{self.atlos_url}/api/v2/source_material/{atlos_id}",
            headers={"Authorization": f"Bearer {self.api_token}"},
        ).json()["result"]
        existing_media = [x["file_hash_sha256"] for x in source_material.get("artifacts", [])]
        if media_hash in existing_media:
            logger.info(f"{media.filename} with SHA256 {media_hash} already uploaded to Atlos")
            return True
        
        # Upload the media to the Atlos API
        requests.post(
            f"{self.atlos_url}/api/v2/source_material/upload/{atlos_id}",
            headers={"Authorization": f"Bearer {self.api_token}"},
            params={
                "title": media.properties
            },
            files={"file": (os.path.basename(media.filename), open(media.filename, "rb"))},
        ).raise_for_status()

        logger.info(f"Uploaded {media.filename} to Atlos with ID {atlos_id} and title {media.key}")
        
        return True

    # must be implemented even if unused
    def uploadf(self, file: IO[bytes], key: str, **kwargs: dict) -> bool: pass
