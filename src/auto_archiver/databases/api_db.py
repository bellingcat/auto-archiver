from typing import Union
import requests, os
from loguru import logger

from . import Database
from ..core import Metadata


class AAApiDb(Database):
    """
        Connects to auto-archiver-api instance
    """
    name = "auto_archiver_api_db"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        self.allow_rearchive = bool(self.allow_rearchive)
        self.assert_valid_string("api_endpoint")
        self.assert_valid_string("api_secret")

    @staticmethod
    def configs() -> dict:
        return {
            "api_endpoint": {"default": None, "help": "API endpoint where calls are made to"},
            "api_secret": {"default": None, "help": "API Basic authentication secret [deprecating soon]"},
            "api_token": {"default": None, "help": "API Bearer token, to be preferred over secret (Basic auth) going forward"},
            "public": {"default": False, "help": "whether the URL should be publicly available via the API"},
            "author_id": {"default": None, "help": "which email to assign as author"},
            "group_id": {"default": None, "help": "which group of users have access to the archive in case public=false as author"},
            "allow_rearchive": {"default": True, "help": "if False then the API database will be queried prior to any archiving operations and stop if the link has already been archived"},
            "tags": {"default": [], "help": "what tags to add to the archived URL", "cli_set": lambda cli_val, cur_val: set(cli_val.split(","))},
        }
    def fetch(self, item: Metadata) -> Union[Metadata, bool]:
        """ query the database for the existence of this item"""
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
        if cached: 
            logger.debug(f"skipping saving archive of {item.get_url()} to the AA API because it was cached")
            return
        logger.debug(f"saving archive of {item.get_url()} to the AA API.")

        payload = {'result': item.to_json(), 'public': self.public, 'author_id': self.author_id, 'group_id': self.group_id, 'tags': list(self.tags)}
        response = requests.post(os.path.join(self.api_endpoint, "submit-archive"), json=payload, auth=("abc", self.api_secret))

        if response.status_code == 200:
            logger.success(f"AA API: {response.json()}")
        else:
            logger.error(f"AA API FAIL ({response.status_code}): {response.json()}")

    