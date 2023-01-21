
from __future__ import annotations
from ast import List
from typing import Any
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
import mimetypes

# annotation order matters
@dataclass_json
@dataclass
class Media:
    filename: str
    key: str = None
    urls: List[str] = field(default_factory=list)
    _mimetype: str = None  # eg: image/jpeg
    properties: dict = field(default_factory=dict)

    def set(self, key: str, value: Any) -> Media:
        self.properties[key] = value
        return self

    def get(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)

    def add_url(self, url: str) -> None:
        # url can be remote, local, ...
        self.urls.append(url)

    @property  # getter .mimetype
    def mimetype(self) -> str:
        assert self.filename is not None and len(self.filename) > 0, "cannot get mimetype from media without filename"
        if not self._mimetype:
            self._mimetype = mimetypes.guess_type(self.filename)[0]
        return self._mimetype or ""

    @mimetype.setter  # setter .mimetype
    def mimetype(self, v: str) -> None:
        self._mimetype = v

    def is_video(self) -> bool:
        return self.mimetype.startswith("video")
