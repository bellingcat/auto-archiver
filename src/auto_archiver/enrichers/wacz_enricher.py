import os, shutil, subprocess, uuid
from loguru import logger

from ..core import Media, Metadata
from . import Enricher
from ..utils import UrlUtil


class WaczEnricher(Enricher):
    """
    Submits the current URL to the webarchive and returns a job_id or completed archive
    """
    name = "wacz_enricher"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {
            "profile": {"default": None, "help": "browsertrix-profile (for profile generation see https://github.com/webrecorder/browsertrix-crawler#creating-and-using-browser-profiles)."},
            "timeout": {"default": 90, "help": "timeout for WACZ generation in seconds"},
            "ignore_auth_wall": {"default": True, "help": "skip URL if it is behind authentication wall, set to False if you have browsertrix profile configured for private content."},
        }

    def enrich(self, to_enrich: Metadata) -> bool:
        # TODO: figure out support for browsertrix in docker
        url = to_enrich.get_url()

        if UrlUtil.is_auth_wall(url):
            logger.debug(f"[SKIP] SCREENSHOT since url is behind AUTH WALL: {url=}")
            return

        logger.debug(f"generating WACZ for {url=}")
        collection = str(uuid.uuid4())[0:8]
        browsertrix_home = os.path.abspath(to_enrich.get_tmp_dir())
        cmd = [
            "docker", "run",
            "--rm",  # delete container once it has completed running
            "-v", f"{browsertrix_home}:/crawls/",
            # "-it", # this leads to "the input device is not a TTY"
            "webrecorder/browsertrix-crawler", "crawl",
            "--url", url,
            "--scopeType", "page",
            "--generateWACZ",
            "--text",
            "--collection", collection,
            "--behaviors", "autoscroll,autoplay,autofetch,siteSpecific",
            "--behaviorTimeout", str(self.timeout),
            "--timeout", str(self.timeout)
        ]
        if self.profile:
            profile_fn = os.path.join(browsertrix_home, "profile.tar.gz")
            shutil.copyfile(self.profile, profile_fn)
            # TODO: test which is right
            cmd.extend(["--profile", profile_fn])
            # cmd.extend(["--profile", "/crawls/profile.tar.gz"])

        try:
            logger.info(f"Running browsertrix-crawler: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
        except Exception as e:
            logger.error(f"WACZ generation failed: {e}")
            return False

        filename = os.path.join(browsertrix_home, "collections", collection, f"{collection}.wacz")
        if not os.path.exists(filename):
            logger.warning(f"Unable to locate and upload WACZ  {filename=}")
            return False

        to_enrich.add_media(Media(filename), "browsertrix")
