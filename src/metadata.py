
from __future__ import annotations
from ast import List
from typing import Any, Union, Dict
from dataclasses import dataclass
from datetime import datetime


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

    # @staticmethod
    def merge(self: Metadata, right: Metadata, overwrite_left=True) -> Metadata:
        # should return a merged version of the Metadata
        # will work for archived() and enriched()
        # what if 2 metadatas contain the same keys? only one can remain! : overwrite_left
        pass

    # TODO: setters?
    def set(self, key: str, val: Any) -> Metadata:
        # goes through metadata and returns the Metadata available
        self.metadata[key] = val
        return self

    def get(self, key: str, default: Any = None) -> Union[Metadata, str]:
        # goes through metadata and returns the Metadata available
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
        return self.get("media", [])

    def set_title(self, title: str) -> Metadata:
        return self.set("title", title)

    def set_timestamp(self, title: datetime) -> Metadata:
        return self.set("title", title)

    def add_media(self, filename: str) -> Metadata:
        return self.get_media().append(filename)

    def as_json(self) -> str:
        # converts all metadata and data into JSON
        pass
