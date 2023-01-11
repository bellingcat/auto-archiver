
from __future__ import annotations
from ast import List
from typing import Any, Union, Dict
from dataclasses import dataclass
import mimetypes


@dataclass
class Media:
    filename: str
    key: str = None
    cdn_url: str = None
    mimetype: str = None  # eg: image/jpeg
    id: str = None # in case this type of media needs a special id, eg: screenshot
    # hash: str = None # TODO: added by enrichers

    def set_mimetype(self) -> Media:
        if not self.mimetype:
            self.mimetype = mimetypes.guess_type(self.filename)[0]
        return self

    def is_video(self) -> bool:
        return self.mimetype.startswith("video")
