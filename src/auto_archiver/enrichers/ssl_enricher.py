import ssl, os
from slugify import slugify
from urllib.parse import urlparse
from loguru import logger

from . import Enricher
from ..core import Metadata, ArchivingContext, Media


class SSLEnricher(Enricher):
    """
    Retrieves SSL certificate information for a domain, as a file
    """
    name = "ssl_enricher"

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self. skip_when_nothing_archived = bool(self.skip_when_nothing_archived)

    @staticmethod
    def configs() -> dict:
        return {
            "skip_when_nothing_archived": {"default": True, "help": "if true, will skip enriching when no media is archived"},
        }

    def enrich(self, to_enrich: Metadata) -> None:
        if not to_enrich.media and self.skip_when_nothing_archived: return
        
        url = to_enrich.get_url()
        domain = urlparse(url).netloc
        logger.debug(f"fetching SSL certificate for {domain=} in {url=}")

        cert = ssl.get_server_certificate((domain, 443))
        cert_fn = os.path.join(ArchivingContext.get_tmp_dir(), f"{slugify(domain)}.pem")
        with open(cert_fn, "w") as f: f.write(cert)
        to_enrich.add_media(Media(filename=cert_fn), id="ssl_certificate")
