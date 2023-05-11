from __future__ import annotations
from dataclasses import dataclass
from abc import abstractmethod
from ..core import Metadata
from ..core import Step


@dataclass
class Feeder(Step):
    name = "feeder"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    def init(name: str, config: dict) -> Feeder:
        # only for code typing
        return Step.init(name, config, Feeder)

    @abstractmethod
    def __iter__(self) -> Metadata: return None