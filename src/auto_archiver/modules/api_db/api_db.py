from typing import Union

import os
import requests
from auto_archiver.utils.custom_logger import logger

from auto_archiver.core import Database
from auto_archiver.core import Metadata


class AAApiDb(Database):
    """Connects to auto-archiver-api instance"""

    def fetch(self, item: Metadata) -> Union[Metadata, bool]:
        """query the database for the existence of this item.
        Helps avoid re-archiving the same URL multiple times.
        """
        if not self.use_api_cache:
            return

        params = {"url": item.get_url(), "limit": 15}
        headers = {"Authorization": f"Bearer {self.api_token}", "accept": "application/json"}
        response = requests.get(os.path.join(self.api_endpoint, "url/search"), params=params, headers=headers)

        if response.status_code == 200:
            if len(response.json()):
                logger.success(f"API returned {len(response.json())} previously archived instance(s)")
                fetched_metadata = [Metadata.from_dict(r["result"]) for r in response.json()]
                return Metadata.choose_most_complete(fetched_metadata)
        else:
            logger.error(f"AA API FAIL ({response.status_code}): {response.json()}")
        return False

    def done(self, item: Metadata, cached: bool = False) -> None:
        """archival result ready - should be saved to DB"""
        if not self.store_results:
            return
        if cached:
            logger.debug("Skipping saving archive to AA API because it was cached")
            return
        logger.debug("Saving archive to the AA API.")

        payload = {
            "author_id": self.author_id,
            "url": item.get_url(),
            "public": self.public,
            "group_id": self.group_id,
            "tags": list(self.tags),
            "result": item.to_json(),
        }
        headers = {"Authorization": f"Bearer {self.api_token}"}
        response = requests.post(
            os.path.join(self.api_endpoint, "interop/submit-archive"), json=payload, headers=headers
        )

        if response.status_code == 201:
            logger.success(f"AA API: {response.json()}")
        else:
            logger.error(f"AA API FAIL ({response.status_code}): {response.json()}")
