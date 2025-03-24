import ssl
import os
from slugify import slugify
from urllib.parse import urlparse
from loguru import logger

from auto_archiver.core import Enricher
from auto_archiver.core import Metadata, Media


class SSLEnricher(Enricher):
    """
    Retrieves SSL certificate information for a domain, as a file
    """

    def enrich(self, to_enrich: Metadata) -> None:
        if not to_enrich.media and self.skip_when_nothing_archived:
            return

        url = to_enrich.get_url()
        parsed = urlparse(url)
        assert parsed.scheme in ["https"], f"Invalid URL scheme {url=}"

        domain = parsed.netloc
        logger.debug(f"fetching SSL certificate for {domain=} in {url=}")

        cert = ssl.get_server_certificate((domain, 443))
        cert_fn = os.path.join(self.tmp_dir, f"{slugify(domain)}.pem")
        with open(cert_fn, "w") as f:
            f.write(cert)
        to_enrich.add_media(Media(filename=cert_fn), id="ssl_certificate")
