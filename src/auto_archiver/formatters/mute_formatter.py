from __future__ import annotations
from dataclasses import dataclass

from ..core import Metadata, Media
from . import Formatter


@dataclass
class MuteFormatter(Formatter):
    name = "mute_formatter"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    def format(self, item: Metadata) -> Media: return None
