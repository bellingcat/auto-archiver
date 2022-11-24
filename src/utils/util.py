from __future__ import annotations
from dataclasses import dataclass
from abc import abstractmethod, ABC
from metadata import Metadata
from step import Step

@dataclass
class Util(Step, ABC):
    name = "util"

    def __init__(self, config: dict) -> None:
        Step.__init__(self)
        
    # only for typing...
    def init(name: str, config: dict) -> Util:
        return super().init(name, config, Util)

    @abstractmethod
    def enrich(self, item: Metadata) -> Metadata: pass
