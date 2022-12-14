
from __future__ import annotations
from ast import List
from typing import Any, Union, Dict
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class Metadata:
    # does not handle files, only primitives
    # the only piece of logic to handle files is the archiver, enricher, and storage
    status: str
    # title: str
    # url: str
    # hash: str
    metadata: Dict[str, Any]

    # TODO: remove and use default?
    def __init__(self, status="") -> None:
        self.status = status
        self.metadata = {}

    def merge(self: Metadata, right: Metadata, overwrite_left=True) -> Metadata:
        """
        merges to Metadata instances, will overwrite according to overwrite_left flag
        """
        res = Metadata()
        if overwrite_left:
            res.status = right.status
            res.metadata = dict(self.metadata)  # make a copy
            for k, v in right.metadata.items():
                print(type(v), type(self.get(k)))
                # assert type(v) == type(self.get(k))
                if type(v) not in [dict, list, set] or k not in res.metadata:
                    res.set(k, v)
                else:  # key conflict
                    if type(v) in [dict, set]: res.set(k, self.get(k) | v)
                    elif type(v) == list: res.set(k, self.get(k) + v)
        else:  # invert and do same logic
            return right.merge(self)
        return res

    # TODO: setters?
    def set(self, key: str, val: Any) -> Metadata:
        # goes through metadata and returns the Metadata available
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

    def get_media(self) -> List:
        return self.get("media", [], create_if_missing=True)

    def set_content(self, content: str) -> Metadata:
        # the main textual content/information from a social media post, webpage, ...
        return self.set("content", content)

    def set_title(self, title: str) -> Metadata:
        return self.set("title", title)

    def set_timestamp(self, title: datetime) -> Metadata:
        return self.set("title", title)

    def add_media(self, filename: str) -> Metadata:
        # print(f"adding {filename} to {self.metadata.get('media')}")
        # return self.set("media", self.get_media() + [filename])
        return self.get_media().append(filename)

    def as_json(self) -> str:
        # converts all metadata and data into JSON
        return json.dumps(self.metadata)
