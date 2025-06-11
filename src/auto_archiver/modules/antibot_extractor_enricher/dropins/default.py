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
