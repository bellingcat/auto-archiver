from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
from metadata import Metadata
from steps.step import Step


@dataclass
class Archiverv2(Step):
    name = "archiver"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        # self.setup()

    # only for typing...
    def init(name: str, config: dict) -> Archiverv2:
        return Step.init(name, config, Archiverv2)

    def setup(self) -> None:
        # used when archivers need to login or do other one-time setup
        pass

    @abstractmethod
    def download(self, item: Metadata) -> Metadata: pass
