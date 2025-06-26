from __future__ import annotations
import mimetypes
import os
import pathlib
from jinja2 import Environment, FileSystemLoader
from urllib.parse import quote
from auto_archiver.utils.custom_logger import logger
import json
import base64

from auto_archiver.version import __version__
from auto_archiver.core import Metadata, Media
from auto_archiver.core import Formatter
from auto_archiver.utils.misc import random_str


class HtmlFormatter(Formatter):
    environment: Environment = None
    template: any = None

    def setup(self) -> None:
        """Sets up the Jinja2 environment and loads the template."""
        template_dir = os.path.join(pathlib.Path(__file__).parent.resolve(), "templates/")
        self.environment = Environment(loader=FileSystemLoader(template_dir), autoescape=True)

        # JinjaHelper class static methods are added as filters
        self.environment.filters.update(
            {k: v.__func__ for k, v in JinjaHelpers.__dict__.items() if isinstance(v, staticmethod)}
        )

        # Load a specific template or default to "html_template.html"
        template_name = self.config.get("template_name", "html_template.html")
        self.template = self.environment.get_template(template_name)

    def format(self, item: Metadata) -> Media:
        url = item.get_url()
        if item.is_empty():
            logger.debug("Nothing to format, skipping")
            return

        content = self.template.render(
            url=url, title=item.get_title(), media=item.media, metadata=item.metadata, version=__version__
        )

        html_path = os.path.join(self.tmp_dir, f"formatted{random_str(24)}.html")
        with open(html_path, mode="w", encoding="utf-8") as outf:
            outf.write(content)
        final_media = Media(filename=html_path, _mimetype="text/html")

        # get the already instantiated hash_enricher module
        he = self.module_factory.get_module("hash_enricher", self.config)
        if len(hd := he.calculate_hash(final_media.filename)):
            final_media.set("hash", f"{he.algorithm}:{hd}")

        return final_media


# JINJA helper filters
class JinjaHelpers:
    @staticmethod
    def is_list(v) -> bool:
        return isinstance(v, list)

    @staticmethod
    def is_video(s: str) -> bool:
        m = mimetypes.guess_type(s)[0]
        return "video" in (m or "")

    @staticmethod
    def is_image(s: str) -> bool:
        m = mimetypes.guess_type(s)[0]
        return "image" in (m or "")

    @staticmethod
    def is_audio(s: str) -> bool:
        m = mimetypes.guess_type(s)[0]
        return "audio" in (m or "")

    @staticmethod
    def is_media(v) -> bool:
        return isinstance(v, Media)

    @staticmethod
    def get_extension(filename: str) -> str:
        return os.path.splitext(filename)[1]

    @staticmethod
    def quote(s: str) -> str:
        return quote(s)

    @staticmethod
    def json_dump_b64(d: dict) -> str:
        j = json.dumps(d, indent=4, default=str)
        return base64.b64encode(j.encode()).decode()
