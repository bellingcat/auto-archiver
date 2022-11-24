from __future__ import annotations
from dataclasses import dataclass, field
from inspect import ClassFoundException
from typing import Type
from metadata import Metadata
from abc import ABC
# from collections.abc import Iterable


@dataclass
class Step(ABC):
    name: str = None

    def __init__(self, config: dict) -> None:
        # reads the configs into object properties
        # self.config = config[self.name]
        for k, v in config[self.name].items():
            self.__setattr__(k, v)

    @staticmethod
    def configs() -> dict: {}

    def init(name: str, config: dict, child: Type[Step]) -> Step:
        """
        cannot find subclasses of child.subclasses
        """
        for sub in child.__subclasses__():
            if sub.name == name:
                print(sub.name, "CALLING NEW")
                return sub(config)
        raise ClassFoundException(f"Unable to initialize STEP with {name=}")

    def get_url(self, item: Metadata) -> str:
        url = item.get("url")
        assert type(url) is str and len(url) > 0
        return url
