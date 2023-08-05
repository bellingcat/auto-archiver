
from __future__ import annotations
import os
import traceback
from typing import Any, List
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
import mimetypes

import ffmpeg
from ffmpeg._run import Error

from .context import ArchivingContext

from loguru import logger


@dataclass_json  # annotation order matters
@dataclass
class Media:
    filename: str
    key: str = None
    urls: List[str] = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    _mimetype: str = None  # eg: image/jpeg
    _stored: bool = field(default=False, repr=False, metadata=config(exclude=lambda _: True))  # always exclude

    def store(self: Media, override_storages: List = None, url: str = "url-not-available"):
        # stores the media into the provided/available storages [Storage]
        # repeats the process for its properties, in case they have inner media themselves
        # for now it only goes down 1 level but it's easy to make it recursive if needed
        storages = override_storages or ArchivingContext.get("storages")
        if not len(storages):
            logger.warning(f"No storages found in local context or provided directly for {self.filename}.")
            return

        for s in storages:
            for any_media in self.all_inner_media(include_self=True):
                s.store(any_media, url)

    def all_inner_media(self, include_self=False):
        """ Media can be inside media properties, examples include transformations on original media.
        This function returns a generator for all the inner media.        
        """
        if include_self: yield self
        for prop in self.properties.values():
            if isinstance(prop, Media): yield prop
            if isinstance(prop, list):
                for prop_media in prop:
                    if isinstance(prop_media, Media): yield prop_media

    def is_stored(self) -> bool:
        return len(self.urls) > 0 and len(self.urls) == len(ArchivingContext.get("storages"))

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

    def is_audio(self) -> bool:
        return self.mimetype.startswith("audio")

    def is_image(self) -> bool:
        return self.mimetype.startswith("image")

    def is_valid_video(self) -> bool:
        # checks for video streams with ffmpeg, or min file size for a video
        # self.is_video() should be used together with this method
        try:
            streams = ffmpeg.probe(self.filename, select_streams='v')['streams']
            logger.warning(f"STREAMS FOR {self.filename} {streams}")
            return any(s.get("duration_ts", 0) > 0 for s in streams)
        except Error: return False # ffmpeg errors when reading bad files
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            try:
                fsize = os.path.getsize(self.filename)
                return fsize > 20_000
            except: pass
        return True
