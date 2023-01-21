from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
from ..core import Metadata, Step

#TODO: likely unused
@dataclass
class Util(Step):
    name = "util"

    def __init__(self, config: dict) -> None:
        Step.__init__(self)
        
    # only for typing...
    def init(name: str, config: dict) -> Util:
        return super().init(name, config, Util)

    @abstractmethod
    def enrich(self, item: Metadata) -> Metadata: pass
