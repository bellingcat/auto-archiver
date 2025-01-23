from typing import Union
import requests, os
from loguru import logger

from auto_archiver.base_modules import Database
from auto_archiver.core import Metadata


class AAApiDb(Database):
    """
        Connects to auto-archiver-api instance
    """
    name = "auto_archiver_api_db"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        self.allow_rearchive = bool(self.allow_rearchive)
        self.store_results = bool(self.store_results)
        self.assert_valid_string("api_endpoint")


    def fetch(self, item: Metadata) -> Union[Metadata, bool]:
        """ query the database for the existence of this item.
            Helps avoid re-archiving the same URL multiple times.
        """
        if not self.allow_rearchive: return
        
        params = {"url": item.get_url(), "limit": 15}
        headers = {"Authorization": f"Bearer {self.api_token}", "accept": "application/json"}
        response = requests.get(os.path.join(self.api_endpoint, "tasks/search-url"), params=params, headers=headers)

        if response.status_code == 200:
            if len(response.json()):
                logger.success(f"API returned {len(response.json())} previously archived instance(s)")
                fetched_metadata = [Metadata.from_dict(r["result"]) for r in response.json()]
                return Metadata.choose_most_complete(fetched_metadata)
        else:
            logger.error(f"AA API FAIL ({response.status_code}): {response.json()}")
        return False


    def done(self, item: Metadata, cached: bool=False) -> None:
        """archival result ready - should be saved to DB"""
        if not self.store_results: return
        if cached: 
            logger.debug(f"skipping saving archive of {item.get_url()} to the AA API because it was cached")
            return
        logger.debug(f"saving archive of {item.get_url()} to the AA API.")

        payload = {'result': item.to_json(), 'public': self.public, 'author_id': self.author_id, 'group_id': self.group_id, 'tags': list(self.tags)}
        headers = {"Authorization": f"Bearer {self.api_token}"}
        response = requests.post(os.path.join(self.api_endpoint, "submit-archive"), json=payload, headers=headers)

        if response.status_code == 200:
            logger.success(f"AA API: {response.json()}")
        else:
            logger.error(f"AA API FAIL ({response.status_code}): {response.json()}")

