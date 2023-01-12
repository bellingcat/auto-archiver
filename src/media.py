
from __future__ import annotations
from ast import List
from typing import Any, Union, Dict
from dataclasses import dataclass, field
import mimetypes


@dataclass
class Media:
    filename: str
    key: str = None
    urls: List[str] = field(default_factory=list)
    _mimetype: str = None  # eg: image/jpeg
    id: str = ""  # in case this type of media needs a special id, eg: screenshot
    # hash: str = None # TODO: added by enrichers

    def add_url(self, url: str) -> None:
        # url can be remote, local, ...
        self.urls.append(url)

    @property  # getter .mimetype
    def mimetype(self) -> str:
        assert self.filename is not None and len(self.filename) > 0, "cannot get mimetype from media without filename"
        if not self._mimetype:
            self._mimetype = mimetypes.guess_type(self.filename)[0]
        return self._mimetype

    @mimetype.setter  # setter .mimetype
    def mimetype(self, v: str) -> None:
        self._mimetype = v

    def is_video(self) -> bool:
        return self._mimetype.startswith("video")
