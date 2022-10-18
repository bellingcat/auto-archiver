
from dataclasses import dataclass


@dataclass
class InstagramConfig:
    username: str
    password: str
    session_file: str
