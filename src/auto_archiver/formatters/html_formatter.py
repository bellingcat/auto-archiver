from __future__ import annotations
from dataclasses import dataclass
import mimetypes, os, pathlib
from jinja2 import Environment, FileSystemLoader
from urllib.parse import quote
from loguru import logger
import minify_html

from ..version import __version__
from ..core import Metadata, Media, ArchivingContext
from . import Formatter
from ..enrichers import HashEnricher
from ..utils.misc import random_str


@dataclass
class HtmlFormatter(Formatter):
    name = "html_formatter"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        self.environment = Environment(loader=FileSystemLoader(os.path.join(pathlib.Path(__file__).parent.resolve(), "templates/")))
        # JinjaHelper class static methods are added as filters
        self.environment.filters.update({
            k: v.__func__ for k, v in JinjaHelpers.__dict__.items() if isinstance(v, staticmethod)
        })
        self.template = self.environment.get_template("html_template.html")

    @staticmethod
    def configs() -> dict:
        return {
            "detect_thumbnails": {"default": True, "help": "if true will group by thumbnails generated by thumbnail enricher by id 'thumbnail_00'"}
        }

    def format(self, item: Metadata) -> Media:
        url = item.get_url()
        if item.is_empty():
            logger.debug(f"[SKIP] FORMAT there is no media or metadata to format: {url=}")
            return

        content = self.template.render(
            url=url,
            title=item.get_title(),
            media=item.media,
            metadata=item.metadata,
            version=__version__
        )
        content = minify_html.minify(content, minify_js=False, minify_css=True)

        html_path = os.path.join(ArchivingContext.get_tmp_dir(), f"formatted{random_str(24)}.html")
        with open(html_path, mode="w", encoding="utf-8") as outf:
            outf.write(content)
        final_media = Media(filename=html_path, _mimetype="text/html")

        he = HashEnricher({"hash_enricher": {"algorithm": ArchivingContext.get("hash_enricher.algorithm"), "chunksize": 1.6e7}})
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
