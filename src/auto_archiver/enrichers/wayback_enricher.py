from loguru import logger
import time, requests

from . import Enricher
from ..archivers import Archiver
from ..utils import UrlUtil
from ..core import Metadata

class WaybackArchiverEnricher(Enricher, Archiver):
    """
    Submits the current URL to the webarchive and returns a job_id or completed archive.

    The Wayback machine will rate-limit IP heavy usage. 
    """
    name = "wayback_archiver_enricher"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        assert type(self.secret) == str and len(self.secret) > 0, "please provide a value for the wayback_enricher API key"
        assert type(self.secret) == str and len(self.secret) > 0, "please provide a value for the wayback_enricher API secret"

    @staticmethod
    def configs() -> dict:
        return {
            "timeout": {"default": 15, "help": "seconds to wait for successful archive confirmation from wayback, if more than this passes the result contains the job_id so the status can later be checked manually."},
            "if_not_archived_within": {"default": None, "help": "only tell wayback to archive if no archive is available before the number of seconds specified, use None to ignore this option. For more information: https://docs.google.com/document/d/1Nsv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA"},
            "key": {"default": None, "help": "wayback API key. to get credentials visit https://archive.org/account/s3.php"},
            "secret": {"default": None, "help": "wayback API secret. to get credentials visit https://archive.org/account/s3.php"},
            "proxy_http": {"default": None, "help": "http proxy to use for wayback requests, eg http://proxy-user:password@proxy-ip:port"},
            "proxy_https": {"default": None, "help": "https proxy to use for wayback requests, eg https://proxy-user:password@proxy-ip:port"},
        }

    def download(self, item: Metadata) -> Metadata:
        # this new Metadata object is required to avoid duplication
        result = Metadata()
        result.merge(item)
        if self.enrich(result):
            return result.success("wayback")

    def enrich(self, to_enrich: Metadata) -> bool:
        proxies = {}
        if self.proxy_http: proxies["http"] = self.proxy_http
        if self.proxy_https: proxies["https"] = self.proxy_https

        url = to_enrich.get_url()
        if UrlUtil.is_auth_wall(url):
            logger.debug(f"[SKIP] WAYBACK since url is behind AUTH WALL: {url=}")
            return

        logger.debug(f"calling wayback for {url=}")

        if to_enrich.get("wayback"):
            logger.info(f"Wayback enricher had already been executed: {to_enrich.get('wayback')}")
            return True

        ia_headers = {
            "Accept": "application/json",
            "Authorization": f"LOW {self.key}:{self.secret}"
        }
        post_data = {'url': url}
        if self.if_not_archived_within:
            post_data["if_not_archived_within"] = self.if_not_archived_within
        # see https://docs.google.com/document/d/1Nsv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA for more options
        r = requests.post('https://web.archive.org/save/', headers=ia_headers, data=post_data, proxies=proxies)

        if r.status_code != 200:
            logger.error(em := f"Internet archive failed with status of {r.status_code}: {r.json()}")
            to_enrich.set("wayback", em)
            return False

        # check job status
        job_id = r.json().get('job_id')
        if not job_id:
            logger.error(f"Wayback failed with {r.json()}")
            return False

        # waits at most timeout seconds until job is completed, otherwise only enriches the job_id information
        start_time = time.time()
        wayback_url = False
        attempt = 1
        while not wayback_url and time.time() - start_time <= self.timeout:
            try:
                logger.debug(f"GETting status for {job_id=} on {url=} ({attempt=})")
                r_status = requests.get(f'https://web.archive.org/save/status/{job_id}', headers=ia_headers, proxies=proxies)
                r_json = r_status.json()
                if r_status.status_code == 200 and r_json['status'] == 'success':
                    wayback_url = f"https://web.archive.org/web/{r_json['timestamp']}/{r_json['original_url']}"
                elif r_status.status_code != 200 or r_json['status'] != 'pending':
                    logger.error(f"Wayback failed with {r_json}")
                    return False
            except requests.exceptions.RequestException as e:
                logger.warning(f"RequestException: fetching status for {url=} due to: {e}")
                break
            except Exception as e:
                logger.warning(f"error fetching status for {url=} due to: {e}")
            if not wayback_url:
                attempt += 1
                time.sleep(1)  # TODO: can be improved with exponential backoff

        if wayback_url:
            to_enrich.set("wayback", wayback_url)
        else:
            to_enrich.set("wayback", {"job_id": job_id, "check_status": f'https://web.archive.org/save/status/{job_id}'})
        to_enrich.set("check wayback", f"https://web.archive.org/web/*/{url}")
        return True
