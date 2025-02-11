import os
from loguru import logger
from tsp_client import TSPSigner, SigningSettings, TSPVerifier
from tsp_client.algorithms import DigestAlgorithm
from importlib.metadata import version
from asn1crypto.cms import ContentInfo
from certvalidator import CertificateValidator, ValidationContext
from asn1crypto import pem
from asn1crypto.core import Asn1Value
import certifi

from auto_archiver.core import Enricher
from auto_archiver.core import Metadata, Media

class TimestampingEnricher(Enricher):
    """
    Uses several RFC3161 Time Stamp Authorities to generate a timestamp token that will be preserved. This can be used to prove that a certain file existed at a certain time, useful for legal purposes, for example, to prove that a certain file was not tampered with after a certain date.

    The information that gets timestamped is concatenation (via paragraphs) of the file hashes existing in the current archive. It will depend on which archivers and enrichers ran before this one. Inner media files (like thumbnails) are not included in the .txt file. It should run AFTER the hash_enricher.

    See https://gist.github.com/Manouchehri/fd754e402d98430243455713efada710 for list of timestamp authorities.
    """

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"RFC3161 timestamping existing files for {url=}")

        # create a new text file with the existing media hashes
        hashes = [m.get("hash").replace("SHA-256:", "").replace("SHA3-512:", "") for m in to_enrich.media if m.get("hash")]

        if not len(hashes):
            logger.warning(f"No hashes found in {url=}")
            return
        
        tmp_dir = self.tmp_dir
        hashes_fn = os.path.join(tmp_dir, "hashes.txt")

        data_to_sign = "\n".join(hashes)
        with open(hashes_fn, "w") as f: 
            f.write(data_to_sign)
        hashes_media = Media(filename=hashes_fn)

        timestamp_tokens = []
        from slugify import slugify
        for tsa_url in self.tsa_urls:
            try:
                message = bytes(data_to_sign, encoding='utf8')
                signed = self.sign_data(tsa_url, message)
                # fail if there's any issue with the certificates, uses certifi list of trusted CAs
                self.verify_signed(signed, message)
                # download and verify timestamping certificate
                cert_chain = self.download_and_verify_certificate(signed)
                # continue with saving the timestamp token
                tst_fn = os.path.join(tmp_dir, f"timestamp_token_{slugify(tsa_url)}")
                with open(tst_fn, "wb") as f: f.write(signed)
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

    def verify_signed(self, signed: bytes, message: bytes) -> None:
        verifier = TSPVerifier(certifi.where())
        verifier.verify(signed, message=message)

    def sign_data(self, tsa_url: str, bytes_data: bytes) -> bytes:
        signing_settings = SigningSettings(tsp_server=tsa_url, digest_algorithm=DigestAlgorithm.SHA256)
        signer = TSPSigner()
        # send TSQ and get TSR from the TSA server
        return signer.sign(message=bytes_data, signing_settings=signing_settings)
    
    def load_tst_certs(self, signed: bytes) -> list[Asn1Value]:
        return ContentInfo.load(signed)["content"]["certificates"]
    
    def download_and_verify_certificate(self, signed: bytes) -> list[Media]:
        # returns the leaf certificate URL, fails if not set
        certificates = self.load_tst_certs(signed)

        trust_roots = []
        with open(certifi.where(), 'rb') as f:
            for _, _, der_bytes in pem.unarmor(f.read(), multiple=True):
                trust_roots.append(der_bytes)
        context = ValidationContext(trust_roots=trust_roots)

        first_cert = certificates[0].dump()
        intermediate_certs = []
        for i in range(1, len(certificates)): # cannot use list comprehension [1:]
            intermediate_certs.append(certificates[i].dump())

        validator = CertificateValidator(first_cert, intermediate_certs=intermediate_certs, validation_context=context)
        path = validator.validate_usage({'digital_signature'}, extended_key_usage={'time_stamping'})

        cert_chain = []
        for cert in path:
            cert_fn = os.path.join(self.tmp_dir, f"{str(cert.serial_number)[:20]}.crt")
            with open(cert_fn, "wb") as f:
                f.write(cert.dump())
            cert_chain.append(Media(filename=cert_fn).set("subject", cert.subject.native["common_name"]))

        return cert_chain
