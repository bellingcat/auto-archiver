import requests
from loguru import logger

from auto_archiver.core import Feeder
from auto_archiver.core import Metadata


class AtlosFeeder(Feeder):

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
