from loguru import logger
import requests

from . import Feeder
from ..core import Metadata, ArchivingContext
from ..utils import get_atlos_config_options


class AtlosFeeder(Feeder):
    name = "atlos_feeder"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        if type(self.api_token) != str:
            raise Exception("Atlos Feeder did not receive an Atlos API token")

    @staticmethod
    def configs() -> dict:
        return get_atlos_config_options()

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
                print(item)
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

        logger.success(f"Processed {count} URL(s)")
