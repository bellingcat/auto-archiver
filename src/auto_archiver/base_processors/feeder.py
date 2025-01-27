from __future__ import annotations
from dataclasses import dataclass
from abc import abstractmethod
from auto_archiver.core import Metadata
from auto_archiver.core import Step


@dataclass
class Feeder(Step):
    name = "feeder"

    @abstractmethod
    def __iter__(self) -> Metadata: return None