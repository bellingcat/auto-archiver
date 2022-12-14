from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
from metadata import Metadata
from steps.step import Step


@dataclass
class StorageV2(Step):
    name = "storage"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    # only for typing...
    def init(name: str, config: dict) -> StorageV2:
        return Step.init(name, config, StorageV2)

    @abstractmethod
    def store(self, item: Metadata) -> Metadata: pass
