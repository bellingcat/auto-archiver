
from __future__ import annotations
from typing import Union, Dict
from dataclasses import dataclass


@dataclass
class Metadata:
    # does not handle files, only primitives
    # the only piece of logic to handle files is the archiver, enricher, and storage
    status: str
    # title: str
    # url: str
    # hash: str
    metadata: Dict[str, Metadata]

    @staticmethod
    def merge(left: Metadata, right: Metadata, overwrite_left=True) -> Metadata:
        # should return a merged version of the Metadata
        # will work for archived() and enriched()
        # what if 2 metadatas contain the same keys? only one can remain! : overwrite_left
        pass

    def get(self, key: str) -> Union[Metadata, str]:
        # goes through metadata and returns the Metadata available
        pass

    def as_json(self) -> str:
        # converts all metadata and data into JSON
        pass
