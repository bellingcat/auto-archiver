import hashlib
import os
from typing import IO, Optional
from typing import Union

import requests
from loguru import logger

from auto_archiver.core import Database
from auto_archiver.core import Feeder
from auto_archiver.core import Media
from auto_archiver.core import Metadata
from auto_archiver.core import Storage


class AtlosFeederDbStorage(Feeder, Database, Storage):

    def __iter__(self) -> Metadata:
        # Get all the urls from the Atlos API
        count = 0
        cursor = None
        while True:
            response = requests.get(
                f"{self.atlos_url}/api/v2/source_material",
                headers={"Authorization": f"Bearer {self.api_token}"},
                params={"cursor": cursor},
            )
            data = response.json()
            response.raise_for_status()
            cursor = data["next"]

            for item in data["results"]:
                if (
                    item["source_url"] not in [None, ""]
                    and (
                        item["metadata"]
                        .get("auto_archiver", {})
                        .get("processed", False)
                        != True
                    )
                    and item["visibility"] == "visible"
                    and item["status"] not in ["processing", "pending"]
                ):
                    yield Metadata().set_url(item["source_url"]).set(
                        "atlos_id", item["id"]
                    )
                    count += 1

            if len(data["results"]) == 0 or cursor is None:
                break


    def failed(self, item: Metadata, reason: str) -> None:
        """Update DB accordingly for failure"""
        # If the item has no Atlos ID, there's nothing for us to do
        if not item.metadata.get("atlos_id"):
            logger.info(f"Item {item.get_url()} has no Atlos ID, skipping")
            return

        requests.post(
            f"{self.atlos_url}/api/v2/source_material/metadata/{item.metadata['atlos_id']}/auto_archiver",
            headers={"Authorization": f"Bearer {self.api_token}"},
            json={"metadata": {"processed": True, "status": "error", "error": reason}},
        ).raise_for_status()
        logger.info(
            f"Stored failure for {item.get_url()} (ID {item.metadata['atlos_id']}) on Atlos: {reason}"
        )

    def fetch(self, item: Metadata) -> Union[Metadata, bool]:
        """check and fetch if the given item has been archived already, each
        database should handle its own caching, and configuration mechanisms"""
        return False

    def _process_metadata(self, item: Metadata) -> dict:
        """Process metadata for storage on Atlos. Will convert any datetime
        objects to ISO format."""

        return {
            k: v.isoformat() if hasattr(v, "isoformat") else v
            for k, v in item.metadata.items()
        }

    def done(self, item: Metadata, cached: bool = False) -> None:
        """archival result ready - should be saved to DB"""

        if not item.metadata.get("atlos_id"):
            logger.info(f"Item {item.get_url()} has no Atlos ID, skipping")
            return

        requests.post(
            f"{self.atlos_url}/api/v2/source_material/metadata/{item.metadata['atlos_id']}/auto_archiver",
            headers={"Authorization": f"Bearer {self.api_token}"},
            json={
                "metadata": dict(
                    processed=True,
                    status="success",
                    results=self._process_metadata(item),
                )
            },
        ).raise_for_status()

        logger.info(
            f"Stored success for {item.get_url()} (ID {item.metadata['atlos_id']}) on Atlos"
        )

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

    def upload(self, media: Media, metadata: Optional[Metadata] = None, **_kwargs) -> bool:
        atlos_id = metadata.get("atlos_id")
        if atlos_id is None:
            logger.error(f"No Atlos ID found in metadata; can't store {media.filename} on Atlos")
            return False

        media_hash = self._hash(media)
        # media_hash = calculate_file_hash(media.filename, hash_algo=hashlib.sha256, chunksize=4096)

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
    def uploadf(self, file: IO[bytes], key: str, **kwargs: dict) -> bool:
        pass
