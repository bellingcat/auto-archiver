from __future__ import annotations
from dataclasses import dataclass
from abc import abstractmethod
from ..core import Metadata, Media, Step


@dataclass
class Formatter(Step):
    name = "formatter"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    def init(name: str, config: dict) -> Formatter:
        # only for code typing
        return Step.init(name, config, Formatter)

    @abstractmethod
    def format(self, item: Metadata) -> Media: return None