from auto_archiver.core.metadata import Metadata
from auto_archiver.modules.antibot_extractor_enricher.dropin import Dropin


class DefaultDropin(Dropin):
    """
    A default fallback drop-in class for handling generic cases in the antibot extractor enricher module.
    """

    @staticmethod
    def suitable(url: str) -> bool:
        return False

    def open_page(self, url) -> bool:
        return True

    def add_extra_media(self, to_enrich: Metadata) -> tuple[int, int]:
        return 0, 0
