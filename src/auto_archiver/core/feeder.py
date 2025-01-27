from __future__ import annotations
from dataclasses import dataclass
from abc import abstractmethod
from auto_archiver.core import Metadata
from auto_archiver.core import BaseModule


@dataclass
class Feeder(BaseModule):

    @abstractmethod
    def __iter__(self) -> Metadata: return None