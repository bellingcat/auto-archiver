import requests
from typing import Union

from loguru import logger

from auto_archiver.core import Database

from auto_archiver.core import Feeder
from auto_archiver.core import Metadata


class AtlosFeederDb(Feeder, Database):

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
