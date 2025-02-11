from __future__ import annotations
from abc import abstractmethod
from auto_archiver.core import Metadata, Media, BaseModule


class Formatter(BaseModule):

    @abstractmethod
    def format(self, item: Metadata) -> Media: return None