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
        self.assert_valid_string("api_endpoint")
        self.assert_valid_string("api_secret")

    @staticmethod
    def configs() -> dict:
        return {
            "api_endpoint": {"default": None, "help": "API endpoint where calls are made to"},
            "api_secret": {"default": None, "help": "API authentication secret"},
            "public": {"default": False, "help": "whether the URL should be publicly available via the API"},
            "author_id": {"default": None, "help": "which email to assign as author"},
            "group_id": {"default": None, "help": "which group of users have access to the archive in case public=false as author"},
            "tags": {"default": [], "help": "what tags to add to the archived URL", "cli_set": lambda cli_val, cur_val: set(cli_val.split(","))},
        }

    def done(self, item: Metadata) -> None:
        """archival result ready - should be saved to DB"""
        logger.info(f"saving archive of {item.get_url()} to the AA API.")

        payload = {'result': item.to_json(), 'public': self.public, 'author_id': self.author_id, 'group_id': self.group_id, 'tags': list(self.tags)}
        response = requests.post(os.path.join(self.api_endpoint, "submit-archive"), json=payload, auth=("abc", self.api_secret))

        if response.status_code == 200:
            logger.success(f"AA API: {response.json()}")
        else:
            logger.error(f"AA API FAIL ({response.status_code}): {response.json()}")
