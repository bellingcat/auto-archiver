from __future__ import annotations
from dataclasses import dataclass
from abc import abstractmethod
from auto_archiver.core import Metadata, Media, BaseModule


@dataclass
class Formatter(BaseModule):

    @abstractmethod
    def format(self, item: Metadata) -> Media: return None