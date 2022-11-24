from __future__ import annotations
from dataclasses import dataclass
from abc import abstractmethod
# from metadata import Metadata
from step import Step


@dataclass
class Feeder(Step):
    name = "feeder"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    def init(name: str, config: dict) -> Feeder:
        # only for code typing
        return Step.init(name, config, Feeder)

    # def feed(self, item: Metadata) -> Metadata: pass

    @abstractmethod
    def __iter__(self) -> Feeder: return None