
from dataclasses import dataclass


@dataclass
class TwitterApiConfig:
    bearer_token: str
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_secret: str
