
from __future__ import annotations
import hashlib
from typing import Any, List, Union, Dict
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
import datetime
from urllib.parse import urlparse
from dateutil.parser import parse as parse_dt
from .media import Media
from .context import ArchivingContext


@dataclass_json  # annotation order matters
@dataclass
class Metadata:
    status: str = "no archiver"
    metadata: Dict[str, Any] = field(default_factory=dict)
    media: List[Media] = field(default_factory=list)

    def __post_init__(self):
        self.set("_processed_at", datetime.datetime.utcnow())

    def merge(self: Metadata, right: Metadata, overwrite_left=True) -> Metadata:
        """
        merges two Metadata instances, will overwrite according to overwrite_left flag
        """
        if not right: return self
        if overwrite_left:
            if right.status and len(right.status):
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

    def store(self: Metadata, override_storages: List = None):
        # calls .store for all contained media. storages [Storage]
        self.remove_duplicate_media_by_hash()
        storages = override_storages or ArchivingContext.get("storages")
        for media in self.media:
            media.store(override_storages=storages, url=self.get_url())

    def set(self, key: str, val: Any) -> Metadata:
        self.metadata[key] = val
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
        return not self.is_success() and len(self.media) == 0 and len(self.metadata) <= 2  # url, processed_at

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
        append_content = (self.get("content", "") + content + "\n").strip()
        return self.set("content", append_content)

    def set_title(self, title: str) -> Metadata:
        return self.set("title", title)

    def get_title(self) -> str:
        return self.get("title")

    def set_timestamp(self, timestamp: datetime.datetime) -> Metadata:
        if type(timestamp) == str:
            timestamp = parse_dt(timestamp)
        assert type(timestamp) == datetime.datetime, "set_timestamp expects a datetime instance"
        return self.set("timestamp", timestamp)

    def get_timestamp(self, utc=True, iso=True) -> datetime.datetime:
        ts = self.get("timestamp")
        if not ts: return 
        if type(ts) == float: ts = datetime.datetime.fromtimestamp(ts)
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

    def remove_duplicate_media_by_hash(self) -> None:
        # iterates all media, calculates a hash if it's missing and deletes duplicates
        def calculate_hash_in_chunks(hash_algo, chunksize, filename) -> str:
            # taken from hash_enricher, cannot be isolated to misc due to circular imports
            with open(filename, "rb") as f:
                while True:
                    buf = f.read(chunksize)
                    if not buf: break
                    hash_algo.update(buf)
            return hash_algo.hexdigest()

        media_hashes = set()
        new_media = []
        for m in self.media:
            h = m.get("hash")
            if not h: h = calculate_hash_in_chunks(hashlib.sha256(), int(1.6e7), m.filename)
            if len(h) and h in media_hashes: continue
            media_hashes.add(h)
            new_media.append(m)
        self.media = new_media

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

    def get_all_media(self) -> List[Media]:
        # returns a list with all the media and inner media
        return [inner for m in self.media for inner in m.all_inner_media(True)]

    def __str__(self) -> str:
        return self.__repr__()


    @staticmethod
    def choose_most_complete(results: List[Metadata]) -> Metadata:
        # returns the most complete result from a list of results
        # prioritizes results with more media, then more metadata
        if len(results) == 0: return None
        if len(results) == 1: return results[0]
        most_complete = results[0]
        for r in results[1:]:
            if len(r.media) > len(most_complete.media): most_complete = r
            elif len(r.media) == len(most_complete.media) and len(r.metadata) > len(most_complete.metadata): most_complete = r
        return most_complete