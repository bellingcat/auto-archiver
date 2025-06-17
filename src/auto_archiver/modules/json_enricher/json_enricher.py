import json
from loguru import logger
import os

from auto_archiver.core import Enricher
from auto_archiver.core import Media, Metadata


class JsonEnricher(Enricher):
    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()

        logger.debug(f"JSON Enricher for {url=}")

        item_path = os.path.join(self.tmp_dir, "metadata.json")
        with open(item_path, mode="w", encoding="utf-8") as outf:
            json.dump(to_enrich.to_dict(), outf, indent=4, default=str, ensure_ascii=False)

        to_enrich.add_media(Media(filename=item_path), id="metadata_json")
