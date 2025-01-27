from __future__ import annotations
from dataclasses import dataclass

from auto_archiver.core import Metadata, Media
from auto_archiver.base_processors import Formatter


@dataclass
class MuteFormatter(Formatter):
    name = "mute_formatter"

    def format(self, item: Metadata) -> Media: return None
