from __future__ import annotations

from auto_archiver.core import Metadata, Media
from auto_archiver.core import Formatter


class MuteFormatter(Formatter):
    def format(self, item: Metadata) -> Media:
        return None
