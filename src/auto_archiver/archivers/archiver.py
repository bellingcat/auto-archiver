from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
import os
import mimetypes, requests
from loguru import logger
from retrying import retry

from ..core import Metadata, Step, ArchivingContext


@dataclass
class Archiver(Step):
    name = "archiver"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    def init(name: str, config: dict) -> Archiver:
        # only for typing...
        return Step.init(name, config, Archiver)

    def setup(self) -> None:
        # used when archivers need to login or do other one-time setup
        pass

    def cleanup(self) -> None:
        # called when archivers are done, or upon errors, cleanup any resources
        pass

    def sanitize_url(self, url: str) -> str:
        # used to clean unnecessary URL parameters OR unfurl redirect links
        return url

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
            to_filename = url.split('/')[-1].split('?')[0]
            if len(to_filename) > 64:
                to_filename = to_filename[-64:]
        to_filename = os.path.join(ArchivingContext.get_tmp_dir(), to_filename)
        if verbose: logger.debug(f"downloading {url[0:50]=} {to_filename=}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
        }
        d = requests.get(url, headers=headers)
        assert d.status_code == 200, f"got response code {d.status_code} for {url=}"
        with open(to_filename, 'wb') as f:
            f.write(d.content)
        return to_filename

    @abstractmethod
    def download(self, item: Metadata) -> Metadata: pass
