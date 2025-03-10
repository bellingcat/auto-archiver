"""The `extractor` module defines the base functionality for implementing extractors in the media archiving framework.
This class provides common utility methods and a standard interface for extractors.

Factory method to initialize an extractor instance based on its name.


"""

from __future__ import annotations
from abc import abstractmethod
import mimetypes
import os
import requests
from loguru import logger
from retrying import retry
import re

from auto_archiver.core import Metadata, BaseModule


class Extractor(BaseModule):
    """
    Base class for implementing extractors in the media archiving framework.
    Subclasses must implement the `download` method to define platform-specific behavior.
    """

    valid_url: re.Pattern = None

    def cleanup(self) -> None:
        """
        Called when extractors are done, or upon errors, cleanup any resources
        """
        pass

    def sanitize_url(self, url: str) -> str:
        """
        Used to clean unnecessary URL parameters OR unfurl redirect links
        """
        return url

    def match_link(self, url: str) -> re.Match:
        """
        Returns a match object if the given URL matches the valid_url pattern or False/None if not.

        Normally used in the `suitable` method to check if the URL is supported by this extractor.

        """
        return self.valid_url.match(url)

    def suitable(self, url: str) -> bool:
        """
        Returns True if this extractor can handle the given URL

        Should be overridden by subclasses

        """
        if self.valid_url:
            return self.match_link(url) is not None

        return True

    def _guess_file_type(self, path: str) -> str:
        """
        Receives a URL or filename and returns global mimetype like 'image' or 'video'
        see https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
        """
        mime = mimetypes.guess_type(path)[0]
        if mime is not None:
            return mime.split("/")[0]
        return ""

    @retry(wait_random_min=500, wait_random_max=3500, stop_max_attempt_number=5)
    def download_from_url(self, url: str, to_filename: str = None, verbose=True) -> str:
        """
        downloads a URL to provided filename, or inferred from URL, returns local filename
        """
        if not to_filename:
            to_filename = url.split("/")[-1].split("?")[0]
            if len(to_filename) > 64:
                to_filename = to_filename[-64:]
        to_filename = os.path.join(self.tmp_dir, to_filename)
        if verbose:
            logger.debug(f"downloading {url[0:50]=} {to_filename=}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
        }
        try:
            d = requests.get(url, stream=True, headers=headers, timeout=30)
            d.raise_for_status()

            # get mimetype from the response headers
            if not mimetypes.guess_type(to_filename)[0]:
                content_type = d.headers.get("Content-Type") or self._guess_file_type(url)
                extension = mimetypes.guess_extension(content_type)
                if extension:
                    to_filename += extension

            with open(to_filename, "wb") as f:
                for chunk in d.iter_content(chunk_size=8192):
                    f.write(chunk)
            return to_filename

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch the Media URL: {e}")

    @abstractmethod
    def download(self, item: Metadata) -> Metadata | False:
        """
        Downloads the media from the given URL and returns a Metadata object with the downloaded media.

        If the URL is not supported or the download fails, this method should return False.

        """
        pass
