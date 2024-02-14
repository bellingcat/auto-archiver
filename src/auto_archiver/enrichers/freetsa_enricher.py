import subprocess, os
from loguru import logger

from . import Enricher
from ..core import Metadata, ArchivingContext, Media


class FreeTSAEnricher(Enricher):
    """
    Uses freeTSA a Time Stamp Authority (https://freetsa.org/index_en.php) to generate two files: a TimeStampRequest .tsq and a TimeStampResponse .tsr . These, in combination with the public certificates available from the TSA, can be used to prove that a certain file existed at a certain time. This is useful for legal purposes, for example, to prove that a certain file was not tampered with after a certain date.

    The information that gets timestamped is a text file with a list of the file hashes existing in the current archive, will depend on which archivers and enrichers ran before this one. Inner media files (like thumbnails) are not included in the .txt file. It should run AFTER the hash_enricher.  
    """
    name = "freetsa_enricher"

    def __init__(self, config: dict) -> None:
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {}

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"Timestamping existing files for {url=}")

        # create a new text file with the existing media hashes
        hashes = [m.get("hash").replace("SHA-256:", "").replace("SHA3-512:", "") for m in to_enrich.media if m.get("hash")]

        if not len(hashes):
            logger.warning(f"No hashes found in {url=}")
            return
        
        tmp_dir = ArchivingContext.get_tmp_dir()
        hashes_fn = os.path.join(tmp_dir, "hashes.txt")

        with open(hashes_fn, "w") as f: f.write("\n".join(hashes))

        # create a TimeStampRequest .tsq
        tsq_fn = os.path.join(tmp_dir, "file.tsq")
        subprocess.run(["openssl", "ts", "-query", "-data", hashes_fn, "-no_nonce", "-sha512", "-out", tsq_fn])

        # send the .tsq to the TSA and get a .tsr
        tsr_fn = os.path.join(tmp_dir, "file.tsr")
        subprocess.run(["curl", "-H", "Content-Type: application/timestamp-query", "--data-binary", f"@{tsq_fn}", "https://freetsa.org/tsr", "-o", tsr_fn], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        assert os.path.exists(tsr_fn), f"Could not find {tsr_fn=} likely an error with the timestamping operation"

        hashes_media = Media(filename=hashes_fn).set("verify", "visit https://freetsa.org/")
        hashes_media.set("timestamp_authority_files", [
            Media(filename=tsq_fn),
            Media(filename=tsr_fn)
        ])

        to_enrich.add_media(hashes_media, id="timestamped_hashes")