import os
from loguru import logger

from importlib.metadata import version

import requests
from rfc3161_client import (
    TimestampRequestBuilder,
    TimeStampResponse,
    decode_timestamp_response,
    VerifierBuilder
)
from rfc3161_client import VerificationError as Rfc3161VerificationError
from rfc3161_client.base import HashAlgorithm
from rfc3161_client.tsp import SignedData
from cryptography import x509
import certifi
from auto_archiver.core import Enricher
from auto_archiver.core import Metadata, Media
from auto_archiver.version import __version__

class TimestampingEnricher(Enricher):
    """
    Uses several RFC3161 Time Stamp Authorities to generate a timestamp token that will be preserved. This can be used to prove that a certain file existed at a certain time, useful for legal purposes, for example, to prove that a certain file was not tampered with after a certain date.

    The information that gets timestamped is concatenation (via paragraphs) of the file hashes existing in the current archive. It will depend on which archivers and enrichers ran before this one. Inner media files (like thumbnails) are not included in the .txt file. It should run AFTER the hash_enricher.

    See https://gist.github.com/Manouchehri/fd754e402d98430243455713efada710 for list of timestamp authorities.
    """

    def setup(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/timestamp-query",
                "User-Agent": f"Auto-Archiver {__version__}",
                "Accept": "application/timestamp-reply",
            }
        )

    def __del__(self) -> None:
        """
        Terminates the underlying network session.
        """
        self.session.close()

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"RFC3161 timestamping existing files for {url=}")

        # create a new text file with the existing media hashes
        hashes = [m.get("hash").replace("SHA-256:", "").replace("SHA3-512:", "") for m in to_enrich.media if m.get("hash")]

        if not len(hashes):
            logger.warning(f"No hashes found in {url=}")
            return
        
        hashes_fn = os.path.join(self.tmp_dir, "hashes.txt")

        data_to_sign = "\n".join(hashes)
        with open(hashes_fn, "w") as f: 
            f.write(data_to_sign)
        hashes_media = Media(filename=hashes_fn)

        timestamp_tokens = []
        from slugify import slugify
        for tsa_url in self.tsa_urls:
            try:
                message = bytes(data_to_sign, encoding='utf8')
                signed: TimeStampResponse = self.sign_data(tsa_url, message)
                # fail if there's any issue with the certificates, uses certifi list of trusted CAs
                self.verify_signed(signed, message)
                # download and verify timestamping certificate
                cert_chain = self.download_certificate(signed)
                # continue with saving the timestamp token
                tst_fn = os.path.join(self.tmp_dir, f"timestamp_token_{slugify(tsa_url)}")
                with open(tst_fn, "wb") as f:
                    f.write(signed)
                timestamp_tokens.append(Media(filename=tst_fn).set("tsa", tsa_url).set("cert_chain", cert_chain))
            except Exception as e:
                logger.warning(f"Error while timestamping {url=} with {tsa_url=}: {e}")

        if len(timestamp_tokens):
            hashes_media.set("timestamp_authority_files", timestamp_tokens)
            hashes_media.set("certifi v", version("certifi"))
            hashes_media.set("tsp_client v", version("tsp_client"))
            hashes_media.set("certvalidator v", version("certvalidator"))
            to_enrich.add_media(hashes_media, id="timestamped_hashes")
            to_enrich.set("timestamped", True)
            logger.success(f"{len(timestamp_tokens)} timestamp tokens created for {url=}")
        else:
            logger.warning(f"No successful timestamps for {url=}")

    def verify_signed(self, timestamp_response: TimeStampResponse, signature: bytes) ->  None:
        """
        Verify a Signed Timestamp using the TSA provided by the Trusted Root.
        """

        trusted_root_path = self.cert_authorities or certifi.where()
        cert_authorities = []

        with open(trusted_root_path, 'rb') as f:
            cert_authorities = x509.load_pem_x509_certificates(f.read())

        if not cert_authorities:
            raise ValueError(f"No trusted roots found in {trusted_root_path}.")
        

        valid = False
        for certificate in cert_authorities:
            builder = VerifierBuilder()
            builder.add_root_certificate(certificate)

            verifier = builder.build()
            try:
                verifier.verify(timestamp_response, signature)
                return certificate
            except Rfc3161VerificationError as e:
                logger.debug(f"Unable to verify Timestamp with CA {certificate.subject}: {e}")
                continue
        
        return False

    def sign_data(self, tsa_url: str, bytes_data: bytes) -> TimeStampResponse:
        # see https://github.com/sigstore/sigstore-python/blob/99948d5b80525a5a104e904ffea58169dc6e0629/sigstore/_internal/timestamp.py#L84-L121

        timestamp_request = (
                TimestampRequestBuilder().data(bytes_data).nonce(nonce=True).build()
            )
        try:
            response = self.session.post(tsa_url, data=timestamp_request.as_bytes(), timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Error while sending request to {tsa_url=}: {e}")
            raise

        # Check that we can parse the response but do not *verify* it
        try:
            timestamp_response = decode_timestamp_response(response.content)
        except ValueError as e:
            logger.error(f"Invalid timestamp response from server {tsa_url}: {e}")
            raise
        return timestamp_response
    
    def load_tst_certs(self, tsp_response: TimeStampResponse):
        signed_data: SignedData = tsp_response.signed_data
        certs = signed_data.certificates

    
    def download_certificate(self, tsp_response: TimeStampResponse) -> list[Media]:
        # returns the leaf certificate URL, fails if not set

        certificates = self.load_tst_certs(tsp_response)


        cert_chain = []
        for cert in path:
            cert_fn = os.path.join(self.tmp_dir, f"{str(cert.serial_number)[:20]}.crt")
            with open(cert_fn, "wb") as f:
                f.write(cert.dump())
            cert_chain.append(Media(filename=cert_fn).set("subject", cert.subject.native["common_name"]))

        return cert_chain
