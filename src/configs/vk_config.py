
from dataclasses import dataclass


@dataclass
class VkConfig:
    username: str
    password: str
    session_file: str
