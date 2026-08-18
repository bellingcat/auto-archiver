import os

from importlib.metadata import version
import hashlib

from slugify import slugify
from retrying import retry
import requests
from auto_archiver.utils.custom_logger import logger

from rfc3161_client import (decode_timestamp_response, TimestampRequestBuilder, TimeStampResponse, VerifierBuilder)
from rfc3161_client import VerificationError as Rfc3161VerificationError
from rfc3161_client.tsp import SignedData
from cryptography import x509
from cryptography.hazmat.primitives import serialization
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

    session = None

    def setup(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/timestamp-query",
                "User-Agent": f"Auto-Archiver {__version__}",
                "Accept": "application/timestamp-reply",
            }
        )

    def cleaup(self) -> None:
        """
        Terminates the underlying network session.
        """
        if self.session:
            self.session.close()

    def enrich(self, to_enrich: Metadata) -> None:
        logger.debug(f"RFC3161 timestamping existing files")

        # create a new text file with the existing media hashes
        hashes = [
            m.get("hash").replace("SHA-256:", "").replace("SHA3-512:", "") for m in to_enrich.media if m.get("hash")
        ]

        if not len(hashes):
            logger.debug(f"No hashes found")
            return

        hashes_fn = os.path.join(self.tmp_dir, "hashes.txt")

        data_to_sign = "\n".join(hashes)
        with open(hashes_fn, "w") as f:
            f.write(data_to_sign)
        hashes_media = Media(filename=hashes_fn)

        timestamp_tokens = []
        for tsa_url in self.tsa_urls:
            try:
                message = bytes(data_to_sign, encoding='utf8')

                logger.debug(f"Timestamping with {tsa_url=}")
                signed: TimeStampResponse = self.sign_data(tsa_url, message)

                # fail if there's any issue with the certificates, uses certifi list of trusted CAs or the user-defined `cert_authorities`
                root_cert = self.verify_signed(signed, message)

                if not root_cert:
                    if self.allow_selfsigned:
                        logger.warning(f"Allowing self-signed certificat from TSA {tsa_url=}")
                    else:
                        raise ValueError(f"No valid root certificate found for {tsa_url=}. Are you sure it's a trusted TSA? Or define an alternative trusted root with `cert_authorities`. (tried: {self.cert_authorities or certifi.where()})")

                # save the timestamping certificate
                cert_chain = self.save_certificate(signed, root_cert)

                timestamp_token_path = self.save_timestamp_token(signed.time_stamp_token(), tsa_url)
                timestamp_tokens.append(Media(filename=timestamp_token_path).set("tsa", tsa_url).set("cert_chain", cert_chain))
            except Exception as e:
                logger.warning(f"Error while timestamping with {tsa_url=}: {e}")

        if len(timestamp_tokens):
            hashes_media.set("timestamp_authority_files", timestamp_tokens)
            hashes_media.set("certifi v", version("certifi"))
            hashes_media.set("rfc3161-client v", version("rfc3161_client"))
            hashes_media.set("cryptography v", version("cryptography"))
            to_enrich.add_media(hashes_media, id="timestamped_hashes")
            to_enrich.set("timestamped", True)
            logger.info(f"{len(timestamp_tokens)} timestamp tokens created")
        else:
            logger.warning(f"No successful timestamps found")

    def save_timestamp_token(self, timestamp_token: bytes, tsa_url: str) -> str:
        """
        Takes a timestamp token, and saves it to a file with the TSA URL as part of the filename.
        """
        tst_path = os.path.join(self.tmp_dir, f"timestamp_token_{slugify(tsa_url)}")
        with open(tst_path, "wb") as f:
            f.write(timestamp_token)
        return tst_path

    def verify_signed(self, timestamp_response: TimeStampResponse, message: bytes) -> x509.Certificate:
        """
        Verify a Signed Timestamp Response is trusted by a known Certificate Authority.

        Args:
            timestamp_response (TimeStampResponse): The signed timestamp response.
            message (bytes): The message that was timestamped.

        Returns:
            x509.Certificate: A valid root certificate that was used to sign the timestamp response, or None

        Raises:
            ValueError: If no valid root certificate was found in the trusted root store.
        """

        trusted_root_path = self.cert_authorities or certifi.where()
        cert_authorities = []

        with open(trusted_root_path, 'rb') as f:
            cert_authorities = x509.load_pem_x509_certificates(f.read())

        if not cert_authorities:
            raise ValueError(f"No trusted roots found in {trusted_root_path}.")

        timestamp_certs = self.tst_certs(timestamp_response)
        intermediate_certs = timestamp_certs[1:-1]

        message_hash = None
        hash_algorithm = timestamp_response.tst_info.message_imprint.hash_algorithm
        if hash_algorithm == x509.ObjectIdentifier(value="2.16.840.1.101.3.4.2.3"):
            message_hash = hashlib.sha512(message).digest()
        elif hash_algorithm == x509.ObjectIdentifier(value="2.16.840.1.101.3.4.2.1"):
            message_hash = hashlib.sha256(message).digest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {hash_algorithm}")

        for certificate in cert_authorities:
            builder = VerifierBuilder()
            builder.add_root_certificate(certificate)

            for intermediate_cert in intermediate_certs:
                builder.add_intermediate_certificate(intermediate_cert)

            verifier = builder.build()

            try:
                verifier.verify(timestamp_response, message_hash)
                return certificate
            except Rfc3161VerificationError:
                continue

        return None

    def sign_data(self, tsa_url: str, bytes_data: bytes) -> TimeStampResponse:
        # see https://github.com/sigstore/sigstore-python/blob/99948d5b80525a5a104e904ffea58169dc6e0629/sigstore/_internal/timestamp.py#L84-L121

        timestamp_request = (
            TimestampRequestBuilder().data(bytes_data).nonce(nonce=True).build()
        )

        @retry(
            wait_exponential_multiplier=1,
            stop_max_attempt_number=2,
        )
        def sign_with_retry():
            response = self.session.post(tsa_url, data=timestamp_request.as_bytes(), timeout=10)
            response.raise_for_status()
            return response

        try:
            response = sign_with_retry()
        except requests.RequestException as e:
            logger.error(f"Error while sending request to {tsa_url=}: {e}")
            raise

        @retry(
            wait_exponential_multiplier=1,
            stop_max_attempt_number=2,
        )
        def decode_with_retry(response):
            return decode_timestamp_response(response.content)
        # Check that we can parse the response but do not *verify* it
        try:
            timestamp_response = decode_with_retry(response)
        except ValueError as e:
            logger.error(f"Invalid timestamp response from server {tsa_url}: {e}")
            raise
        return timestamp_response

    def tst_certs(self, tsp_response: TimeStampResponse):
        signed_data: SignedData = tsp_response.signed_data
        certs = [x509.load_der_x509_certificate(c) for c in signed_data.certificates]
        # reorder the certs to be in the correct order
        ordered_certs = []
        if len(certs) == 1:
            return certs

        while (len(ordered_certs) < len(certs)):
            if len(ordered_certs) == 0:
                for cert in certs:
                    if not [c for c in certs if cert.subject == c.issuer]:
                        ordered_certs.append(cert)
                        break
            else:
                for cert in certs:
                    if cert.subject == ordered_certs[-1].issuer:
                        ordered_certs.append(cert)
                        break
        return ordered_certs

    def save_certificate(self, tsp_response: TimeStampResponse, verified_root_cert: x509.Certificate) -> list[Media]:
        # returns the leaf certificate URL, fails if not set

        certificates = self.tst_certs(tsp_response)

        if verified_root_cert:
            # add the verified root certificate (if there is one - self signed certs will have None here)
            certificates += [verified_root_cert]

        cert_chain = []
        for i, cert in enumerate(certificates):
            cert_fn = os.path.join(self.tmp_dir, f"{i + 1} – {str(cert.serial_number)[:20]}.crt")
            with open(cert_fn, "wb") as f:
                f.write(cert.public_bytes(encoding=serialization.Encoding.PEM))
            cert_chain.append(Media(filename=cert_fn).set("subject", cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value))

        return cert_chain
