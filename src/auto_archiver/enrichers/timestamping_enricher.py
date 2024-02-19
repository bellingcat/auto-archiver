import os
from loguru import logger
from tsp_client import TSPSigner, SigningSettings
from tsp_client.algorithms import DigestAlgorithm

from . import Enricher
from ..core import Metadata, ArchivingContext, Media


class TimestampingEnricher(Enricher):
    """
    Uses several RFC3161 Time Stamp Authorities to generate a timestamp token that will be preserved. This can be used to prove that a certain file existed at a certain time, useful for legal purposes, for example, to prove that a certain file was not tampered with after a certain date.

    The information that gets timestamped is concatenation (via paragraphs) of the file hashes existing in the current archive. It will depend on which archivers and enrichers ran before this one. Inner media files (like thumbnails) are not included in the .txt file. It should run AFTER the hash_enricher.

    See https://gist.github.com/Manouchehri/fd754e402d98430243455713efada710 for list of timestamp authorities.
    """
    name = "timestamping_enricher"

    def __init__(self, config: dict) -> None:
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {
            "tsa_urls": { 
                "default": [
                    # [Adobe Approved Trust List] and [Windows Cert Store]
                    "http://timestamp.digicert.com", 
                    "http://timestamp.identrust.com",
                    "https://timestamp.entrust.net/TSS/RFC3161sha2TS",
                    # "https://timestamp.sectigo.com", # wait 15 seconds between each request.

                    # [Adobe: European Union Trusted Lists].
                    # "https://timestamp.sectigo.com/qualified", # wait 15 seconds between each request.
                    
                    # [Windows Cert Store]
                    "http://timestamp.globalsign.com/tsa/r6advanced1",
                    
                    # [Adobe: European Union Trusted Lists] and [Windows Cert Store]
                    "http://ts.quovadisglobal.com/eu",
                ], 
                "help": "List of RFC3161 Time Stamp Authorities to use, separate with commas if passed via the command line.", 
                "cli_set": lambda cli_val, cur_val: set(cli_val.split(",")) 
            }
        }

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"RFC3161 timestamping existing files for {url=}")

        # create a new text file with the existing media hashes
        hashes = [m.get("hash").replace("SHA-256:", "").replace("SHA3-512:", "") for m in to_enrich.media if m.get("hash")]

        if not len(hashes):
            logger.warning(f"No hashes found in {url=}")
            return
        
        tmp_dir = ArchivingContext.get_tmp_dir()
        hashes_fn = os.path.join(tmp_dir, "hashes.txt")

        data_to_sign = "\n".join(hashes)
        with open(hashes_fn, "w") as f: 
            f.write(data_to_sign)
        hashes_media = Media(filename=hashes_fn)

        timestamp_tokens = []
        from slugify import slugify
        for tsa_url in self.tsa_urls:
            try:
                signing_settings = SigningSettings(tsp_server=tsa_url, digest_algorithm=DigestAlgorithm.SHA256)
                signer = TSPSigner()
                signed = signer.sign(message=bytes(data_to_sign, encoding='utf8'), signing_settings=signing_settings)
                tst_fn = os.path.join(tmp_dir, f"timestamp_token_{slugify(tsa_url)}")
                with open(tst_fn, "wb") as f: f.write(signed)
                timestamp_tokens.append(Media(filename=tst_fn).set("tsa", tsa_url))
            except Exception as e:
                logger.warning(f"Error while timestamping {url=} with {tsa_url=}: {e}")

        if len(timestamp_tokens):
            hashes_media.set("timestamp_authority_files", timestamp_tokens)
            to_enrich.add_media(hashes_media, id="timestamped_hashes")
            to_enrich.set("timestamped", True)
            logger.success(f"{len(timestamp_tokens)} timestamp tokens created for {url=}")
        else:
            logger.warning(f"No successful timestamps for {url=}")