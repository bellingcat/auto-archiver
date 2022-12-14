from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
from metadata import Metadata
from steps.step import Step
import mimetypes, requests


@dataclass
class Archiverv2(Step):
    name = "archiver"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    # only for typing...

    def init(name: str, config: dict) -> Archiverv2:
        return Step.init(name, config, Archiverv2)

    def setup(self) -> None:
        # used when archivers need to login or do other one-time setup
        pass

    def _guess_file_type(self, path: str) -> str:
        """
        Receives a URL or filename and returns global mimetype like 'image' or 'video'
        see https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
        """
        mime = mimetypes.guess_type(path)[0]
        if mime is not None:
            return mime.split("/")[0]
        return ""

    def download_from_url(self, url:str, to_filename:str) -> None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
        }
        d = requests.get(url, headers=headers)
        with open(to_filename, 'wb') as f:
            f.write(d.content)

    @abstractmethod
    def download(self, item: Metadata) -> Metadata: pass
