"""
Manages media files and their associated metadata, supporting storage,
nested media retrieval, and type validation.
"""

from __future__ import annotations
import os
import traceback
from typing import Any, List, Iterator
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
import mimetypes

from loguru import logger


@dataclass_json  # annotation order matters
@dataclass
class Media:
    """
    Represents a media file with associated properties and storage details.

    Attributes:
    - filename: The file path of the media as saved locally (temporarily, before uploading to the storage).
    - urls: A list of URLs where the media is stored or accessible.
    - properties: Additional metadata or transformations for the media.
    - _mimetype: The media's mimetype (e.g., image/jpeg, video/mp4).
    """

    filename: str
    _key: str = None
    urls: List[str] = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    _mimetype: str = None  # eg: image/jpeg
    _stored: bool = field(default=False, repr=False, metadata=config(exclude=lambda _: True))  # always exclude

    def store(self: Media, metadata: Any, url: str = "url-not-available", storages: List[Any] = None) -> None:
        # 'Any' typing for metadata to avoid circular imports. Stores the media
        # into the provided/available storages [Storage] repeats the process for
        # its properties, in case they have inner media themselves for now it
        # only goes down 1 level but it's easy to make it recursive if needed.
        if not len(storages):
            logger.warning(f"No storages found in local context or provided directly for {self.filename}.")
            return

        for s in storages:
            for any_media in self.all_inner_media(include_self=True):
                s.store(any_media, url, metadata=metadata)

    def all_inner_media(self, include_self=False) -> Iterator[Media]:
        """Retrieves all media, including nested media within properties or transformations on original media.
        This function returns a generator for all the inner media.

        """
        if include_self:
            yield self
        for prop in self.properties.values():
            if isinstance(prop, Media):
                for inner_media in prop.all_inner_media(include_self=True):
                    yield inner_media
            if isinstance(prop, list):
                for prop_media in prop:
                    if isinstance(prop_media, Media):
                        for inner_media in prop_media.all_inner_media(include_self=True):
                            yield inner_media

    def is_stored(self, in_storage) -> bool:
        # checks if the media is already stored in the given storage
        return len(self.urls) > 0 and len(self.urls) == len(in_storage.config["steps"]["storages"])

    @property
    def key(self) -> str:
        return self._key

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
        if not self.filename or len(self.filename) == 0:
            logger.warning(f"cannot get mimetype from media without filename: {self}")
            return ""
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
        # Note: this is intentional, to only import ffmpeg here - when the method is called
        # this speeds up loading the module. We check that 'ffmpeg' is available on startup
        # when we load each manifest file
        import ffmpeg
        from ffmpeg._run import Error

        # checks for video streams with ffmpeg, or min file size for a video
        # self.is_video() should be used together with this method
        try:
            streams = ffmpeg.probe(self.filename, select_streams="v")["streams"]
            logger.warning(f"STREAMS FOR {self.filename} {streams}")
            return any(s.get("duration_ts", 0) > 0 for s in streams)
        except Error:
            return False  # ffmpeg errors when reading bad files
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            try:
                fsize = os.path.getsize(self.filename)
                return fsize > 20_000
            except Exception as e:
                pass
        return True
