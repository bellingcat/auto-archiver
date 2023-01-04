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
        for k, v in config.get(self.name, {}).items():
            self.__setattr__(k, v)

    @staticmethod
    def configs() -> dict: {}

    def init(name: str, config: dict, child: Type[Step]) -> Step:
        """
        looks into direct subclasses of child for name and returns such ab object
        TODO: cannot find subclasses of child.subclasses
        """
        for sub in child.__subclasses__():
            if sub.name == name:
                return sub(config)
        raise ClassFoundException(f"Unable to initialize STEP with {name=}")
