import hashlib
import os
from typing import IO, Iterator, Optional, Union

import requests
from auto_archiver.utils.custom_logger import logger

from auto_archiver.core import Database, Feeder, Media, Metadata, Storage
from auto_archiver.utils import calculate_file_hash


class AtlosFeederDbStorage(Feeder, Database, Storage):
    def setup(self) -> requests.Session:
        """create and return a persistent session."""
        self.session = requests.Session()

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Wrapper for GET requests to the Atlos API."""
        url = f"{self.atlos_url}{endpoint}"
        response = self.session.get(url, headers={"Authorization": f"Bearer {self.api_token}"}, params=params)
        response.raise_for_status()
        return response.json()

    def _post(
        self,
        endpoint: str,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
        files: Optional[dict] = None,
    ) -> dict:
        """Wrapper for POST requests to the Atlos API."""
        url = f"{self.atlos_url}{endpoint}"
        response = self.session.post(
            url,
            headers={"Authorization": f"Bearer {self.api_token}"},
            json=json,
            params=params,
            files=files,
        )
        response.raise_for_status()
        return response.json()

    # ! Atlos Module - Feeder Methods

    def __iter__(self) -> Iterator[Metadata]:
        """Iterate over unprocessed, visible source materials from Atlos."""
        cursor = None
        while True:
            data = self._get("/api/v2/source_material", params={"cursor": cursor})
            cursor = data.get("next")
            results = data.get("results", [])
            for item in results:
                if (
                    item.get("source_url") not in [None, ""]
                    and not item.get("metadata", {}).get("auto_archiver", {}).get("processed", False)
                    and item.get("visibility") == "visible"
                    and item.get("status") not in ["processing", "pending"]
                ):
                    yield Metadata().set_url(item["source_url"]).set("atlos_id", item["id"])
            if not results or cursor is None:
                break

    # ! Atlos Module - Database Methods

    def failed(self, item: Metadata, reason: str) -> None:
        """Mark an item as failed in Atlos, if the ID exists."""
        atlos_id = item.metadata.get("atlos_id")
        if not atlos_id:
            logger.info("No Atlos ID available, skipping")
            return
        self._post(
            f"/api/v2/source_material/metadata/{atlos_id}/auto_archiver",
            json={"metadata": {"processed": True, "status": "error", "error": reason}},
        )
        logger.info(f"Stored failure ID {atlos_id} on Atlos: {reason}")

    def fetch(self, item: Metadata) -> Union[Metadata, bool]:
        """check and fetch if the given item has been archived already, each
        database should handle its own caching, and configuration mechanisms"""
        return False

    def _process_metadata(self, item: Metadata) -> dict:
        """Process metadata for storage on Atlos. Will convert any datetime
        objects to ISO format."""
        return {k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in item.metadata.items()}

    def done(self, item: Metadata, cached: bool = False) -> None:
        """Mark an item as successfully archived in Atlos."""
        atlos_id = item.metadata.get("atlos_id")
        if not atlos_id:
            logger.info("Item has no Atlos ID, skipping")
            return
        self._post(
            f"/api/v2/source_material/metadata/{atlos_id}/auto_archiver",
            json={
                "metadata": {
                    "processed": True,
                    "status": "success",
                    "results": self._process_metadata(item),
                }
            },
        )
        logger.info(f"Stored success ID {atlos_id} on Atlos")

    # ! Atlos Module - Storage Methods

    def get_cdn_url(self, _media: Media) -> str:
        """Return the base Atlos URL as the CDN URL."""
        return self.atlos_url

    def upload(self, media: Media, metadata: Optional[Metadata] = None, **_kwargs) -> bool:
        """Upload a media file to Atlos if it has not been uploaded already."""
        if metadata is None:
            logger.error(f"No metadata provided for {media.filename}")
            return False

        atlos_id = metadata.get("atlos_id")
        if not atlos_id:
            logger.error(f"No Atlos ID found in metadata; can't store {media.filename} in Atlos.")
            return False

        media_hash = calculate_file_hash(media.filename, hash_algo=hashlib.sha256, chunksize=4096)

        # Check whether the media has already been uploaded
        source_material = self._get(f"/api/v2/source_material/{atlos_id}")["result"]
        existing_media = [artifact.get("file_hash_sha256") for artifact in source_material.get("artifacts", [])]
        if media_hash in existing_media:
            logger.info(f"{media.filename} with SHA256 {media_hash} already uploaded to Atlos")
            return True

        # Upload the media to the Atlos API
        with open(media.filename, "rb") as file_obj:
            self._post(
                f"/api/v2/source_material/upload/{atlos_id}",
                params={"title": media.properties},
                files={"file": (os.path.basename(media.filename), file_obj)},
            )
        logger.info(f"Uploaded {media.filename} to Atlos with ID {atlos_id} and title {media.key}")
        return True

    def uploadf(self, file: IO[bytes], key: str, **kwargs: dict) -> bool:
        """Upload a file-like object; not implemented."""
        pass
