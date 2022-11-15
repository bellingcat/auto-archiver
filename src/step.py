from __future__ import annotations
from dataclasses import dataclass
from typing import Type
from metadata import Metadata
from abc import ABC


@dataclass
class Step(ABC):
    name : str = None

    def __init__(self, config: dict) -> None:
        self.config = self.config[self.name]

    @staticmethod
    def configs() -> dict: {}

    def init(name: str, config: dict, child: Type[Step]) -> Step:
        """
        cannot find subclasses of child.subclasses
        """
        for sub in child.__subclasses__():
            if sub.name == name:
                return sub.__init__(config)
        raise f"Unable to initialize class with {name=}"

    def get_url(self, item: Metadata) -> str:
        url = item.get("url")
        assert type(url) is str and len(url) > 0
        return url
