import os
from typing import IO, List, Optional
from loguru import logger
import requests

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

    def upload(self, media: Media, metadata: Optional[Metadata]=None, **_kwargs) -> bool:
        atlos_id = metadata.get("atlos_id")
        if atlos_id is None:
            logger.error(f"No Atlos ID found in metadata; can't store {media.filename} on Atlos")
            return False
        
        # Upload the media to the Atlos API
        requests.post(
            f"{self.atlos_url}/api/v2/source_material/upload/{atlos_id}",
            headers={"Authorization": f"Bearer {self.api_token}"},
            json={
                "title": media.key
            },
            files={"file": (os.path.basename(media.filename), open(media.filename, "rb"))},
        ).raise_for_status()

        logger.info(f"Uploaded {media.filename} to Atlos with ID {atlos_id} and title {media.key}")
        
        return True

    # must be implemented even if unused
    def uploadf(self, file: IO[bytes], key: str, **kwargs: dict) -> bool: pass
