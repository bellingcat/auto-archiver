from __future__ import annotations
from dataclasses import dataclass
from abc import abstractmethod, ABC
from ..core import Metadata, Step

@dataclass
class Enricher(Step, ABC):
    name = "enricher"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        

    # only for typing...
    def init(name: str, config: dict) -> Enricher:
        return Step.init(name, config, Enricher)

    @abstractmethod
    def enrich(self, to_enrich: Metadata) -> None: pass
