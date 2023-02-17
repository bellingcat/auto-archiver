
from __future__ import annotations
from ast import List, Set
from typing import Any, Union, Dict
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
import datetime
from urllib.parse import urlparse
from dateutil.parser import parse as parse_dt
from .media import Media


# annotation order matters
@dataclass_json
@dataclass
class Metadata:
    status: str = "no archiver"
    _processed_at: datetime = field(default_factory=datetime.datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tmp_keys: Set[str] = field(default_factory=set, repr=False, metadata={"exclude": True})  # keys that are not to be saved in DBs
    media: List[Media] = field(default_factory=list)
    rearchivable: bool = True  # defaults to true, archivers can overwrite

    def merge(self: Metadata, right: Metadata, overwrite_left=True) -> Metadata:
        """
        merges two Metadata instances, will overwrite according to overwrite_left flag
        """
        if not right: return self
        if overwrite_left:
            if right.status and len(right.status):
                self.status = right.status
            self.rearchivable |= right.rearchivable
            self.tmp_keys |= right.tmp_keys
            for k, v in right.metadata.items():
                assert k not in self.metadata or type(v) == type(self.get(k))
                if type(v) not in [dict, list, set] or k not in self.metadata:
                    self.set(k, v)
                else:  # key conflict
                    if type(v) in [dict, set]: self.set(k, self.get(k) | v)
                    elif type(v) == list: self.set(k, self.get(k) + v)
            self.media.extend(right.media)
        else:  # invert and do same logic
            return right.merge(self)
        return self

    def set(self, key: str, val: Any, is_tmp=False) -> Metadata:
        # if not self.metadata: self.metadata = {}
        self.metadata[key] = val
        if is_tmp: self.tmp_keys.add(key)
        return self

    def get(self, key: str, default: Any = None, create_if_missing=False) -> Union[Metadata, str]:
        # goes through metadata and returns the Metadata available
        if create_if_missing and key not in self.metadata:
            self.metadata[key] = default
        return self.metadata.get(key, default)

    def success(self, context: str = None) -> Metadata:
        if context: self.status = f"{context}: success"
        else: self.status = "success"
        return self

    def is_success(self) -> bool:
        return "success" in self.status

    def is_empty(self) -> bool:
        return not self.is_success() and len(self.media) == 0 and len(self.get_clean_metadata()) <= 2  # url, processed_at

    @property  # getter .netloc
    def netloc(self) -> str:
        return urlparse(self.get_url()).netloc


# custom getter/setters


    def set_url(self, url: str) -> Metadata:
        assert type(url) is str and len(url) > 0, "invalid URL"
        return self.set("url", url)

    def get_url(self) -> str:
        url = self.get("url")
        assert type(url) is str and len(url) > 0, "invalid URL"
        return url

    def set_content(self, content: str) -> Metadata:
        # a dump with all the relevant content
        return self.set("content", content)

    def set_title(self, title: str) -> Metadata:
        return self.set("title", title)

    def get_title(self) -> str:
        return self.get("title")

    def set_tmp_dir(self, tmp_dir: str) -> Metadata:
        return self.set("tmp_dir", tmp_dir, True)

    def get_tmp_dir(self) -> str:
        return self.get("tmp_dir")

    def set_timestamp(self, timestamp: datetime.datetime) -> Metadata:
        if type(timestamp) == str:
            timestamp = parse_dt(timestamp)
        assert type(timestamp) == datetime.datetime, "set_timestamp expects a datetime instance"
        return self.set("timestamp", timestamp)

    def get_timestamp(self, utc=True, iso=True) -> datetime.datetime:
        ts = self.get("timestamp")
        if not ts: return ts
        if utc: ts = ts.replace(tzinfo=datetime.timezone.utc)
        if iso: return ts.isoformat()
        return ts

    def add_media(self, media: Media, id: str = None) -> Metadata:
        # adds a new media, optionally including an id
        if media is None: return
        if id is not None:
            assert not len([1 for m in self.media if m.get("id") == id]), f"cannot add 2 pieces of media with the same id {id}"
            media.set("id", id)
        self.media.append(media)
        return media

    def get_media_by_id(self, id: str, default=None) -> Media:
        for m in self.media:
            if m.get("id") == id: return m
        return default

    def get_first_image(self, default=None) -> Media:
        for m in self.media:
            if "image" in m.mimetype: return m
        return default

    def set_final_media(self, final: Media) -> Metadata:
        """final media is a special type of media: if you can show only 1 this is it, it's useful for some DBs like GsheetDb"""
        self.add_media(final, "_final_media")

    def get_final_media(self) -> Media:
        _default = self.media[0] if len(self.media) else None
        return self.get_media_by_id("_final_media", _default)

    def get_clean_metadata(self) -> Metadata:
        return dict(
            {k: v for k, v in self.metadata.items() if k not in self.tmp_keys},
            **{"processed_at": self._processed_at}
        )
