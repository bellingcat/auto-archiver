from __future__ import annotations
from dataclasses import dataclass
from abc import abstractmethod
from metadata import Metadata
from media import Media
from formatters import Formatter
from jinja2 import Environment, FileSystemLoader
import uuid, os, pathlib


@dataclass
class HtmlFormatter(Formatter):
    name = "html_formatter"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        self.environment = Environment(loader=FileSystemLoader(os.path.join(pathlib.Path(__file__).parent.resolve(), "templates/")))
        self.template = self.environment.get_template("html_template.html")

    @staticmethod
    def configs() -> dict:
        return {}

    def format(self, item: Metadata) -> Media:
        print("FORMATTING")
        content = self.template.render(
            url=item.get_url(),
            title=item.get_title(),
            media=item.media,
            metadata=item.get_clean_metadata()
        )
        html_path = os.path.join(item.get_tmp_dir(), f"formatted{str(uuid.uuid4())}.html")
        with open(html_path, mode="w", encoding="utf-8") as outf:
            outf.write(content)
        return Media(filename=html_path)
