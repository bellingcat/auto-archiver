
from __future__ import annotations
from ast import List
from typing import Any, Union, Dict
from dataclasses import dataclass, field
from datetime import datetime
# import json

from media import Media


@dataclass
class Metadata:
    status: str = ""
    metadata: Dict[str, Any]  = field(default_factory=dict)
    media: List[Media] = field(default_factory=list)

    def merge(self: Metadata, right: Metadata, overwrite_left=True) -> Metadata:
        """
        merges two Metadata instances, will overwrite according to overwrite_left flag
        """
        if overwrite_left:
            self.status = right.status
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

    def set(self, key: str, val: Any) -> Metadata:
        self.metadata[key] = val
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

    def set_timestamp(self, timestamp: datetime) -> Metadata:
        assert type(timestamp) == datetime, "set_timestamp expects a datetime instance"
        return self.set("timestamp", timestamp)

    def add_media(self, media: Media) -> Metadata:
        # print(f"adding {filename} to {self.metadata.get('media')}")
        # return self.set("media", self.get_media() + [filename])
        # return self.get_media().append(media)
        return self.media.append(media)

    # def as_json(self) -> str:
    #     # converts all metadata and data into JSON
    #     return json.dumps(self.metadata)
    #   #TODO: datetime is not serializable
