
from __future__ import annotations
from typing import Any, Union, Dict
from dataclasses import dataclass


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
    def __init__(self) -> None:
        self.status = ""
        self.metadata = {}

    # @staticmethod
    def merge(self: Metadata, right: Metadata, overwrite_left=True) -> Metadata:
        # should return a merged version of the Metadata
        # will work for archived() and enriched()
        # what if 2 metadatas contain the same keys? only one can remain! : overwrite_left
        pass

    # TODO: setters?
    def set(self, key: str, val: Any) -> Union[Metadata, str]:
        # goes through metadata and returns the Metadata available
        self.metadata[key] = val

    def get(self, key: str, default: Any = None) -> Union[Metadata, str]:
        # goes through metadata and returns the Metadata available
        return self.metadata.get(key, default)

    def as_json(self) -> str:
        # converts all metadata and data into JSON
        pass
