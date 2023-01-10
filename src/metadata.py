
from __future__ import annotations
from ast import List, Set
from typing import Any, Union, Dict
from dataclasses import dataclass, field
import datetime, mimetypes
from loguru import logger
# import json

from media import Media


@dataclass
class Metadata:
    status: str = ""
    _processed_at: datetime = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tmp_keys: Set[str] = field(default_factory=set)  # keys that are not to be saved in DBs
    media: List[Media] = field(default_factory=list)
    final_media: Media = None  # can be overwritten by formatters
    rearchivable: bool = False

    # def __init__(self, url, metadata = {}) -> None:
    #     self.set_url(url)
    #     self.metadata = metadata

    def merge(self: Metadata, right: Metadata, overwrite_left=True) -> Metadata:
        """
        merges two Metadata instances, will overwrite according to overwrite_left flag
        """
        if overwrite_left:
            self.status = right.status
            self.rearchivable |= right.rearchivable
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

# custom getter/setters

    def set_url(self, url: str) -> Metadata:
        assert type(url) is str and len(url) > 0, "invalid URL"
        return self.set("url", url)

    def get_url(self) -> str:
        url = self.get("url")
        assert type(url) is str and len(url) > 0, "invalid URL"
        return url

    def set_content(self, content: str) -> Metadata:
        # the main textual content/information from a social media post, webpage, ...
        return self.set("content", content)

    def set_title(self, title: str) -> Metadata:
        return self.set("title", title)

    def get_title(self) -> str:
        return self.get("title")

    def set_timestamp(self, timestamp: datetime.datetime) -> Metadata:
        assert type(timestamp) == datetime.datetime, "set_timestamp expects a datetime instance"
        return self.set("timestamp", timestamp)

    def get_timestamp(self, utc=True, iso=True) -> datetime.datetime:
        ts = self.get("timestamp")
        if not ts: return ts
        if utc: ts = ts.replace(tzinfo=datetime.timezone.utc)
        if iso: return ts.isoformat()
        return ts

    def add_media(self, media: Media) -> Metadata:
        media.set_mimetype()
        return self.media.append(media)

    def set_final_media(self, final: Media) -> Metadata:
        if final:
            if self.final_media:
                logger.warning(f"overwriting final media value :{self.final_media} with {final}")
            final.set_mimetype()
            self.final_media = final
        return self

    def get_single_media(self) -> Media:
        if self.final_media:
            return self.final_media
        return self.media[0]

    # def as_json(self) -> str:
    #     # converts all metadata and data into JSON
    #     return json.dumps(self.metadata)
    #   #TODO: datetime is not serializable

    def get_clean_metadata(self) -> Metadata:
        return dict(
            {k: v for k, v in self.metadata.items() if k not in self.tmp_keys},
            **{"processed_at": self._processed_at}  # TODO: move to enrichment
        )

    def cleanup(self) -> Metadata:
        # TODO: refactor so it returns a JSON with all intended properties, except tmp_keys
        # the code below leads to errors if database needs tmp_keys after they are removed
        # """removes temporary metadata fields, ideally called after all ops except writing"""
        # for tmp_key in self.tmp_keys:
        # self.metadata.pop(tmp_key, None)
        # self.tmp_keys = set()
        pass
