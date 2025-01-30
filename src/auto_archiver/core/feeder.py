from __future__ import annotations
from abc import abstractmethod
from auto_archiver.core import Metadata
from auto_archiver.core import BaseModule

class Feeder(BaseModule):

    @abstractmethod
    def __iter__(self) -> Metadata: return None