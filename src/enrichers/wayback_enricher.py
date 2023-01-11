from utils import Webdriver
from . import Enricher
from metadata import Metadata
from loguru import logger
from selenium.common.exceptions import TimeoutException
import time, requests


class WaybackEnricher(Enricher):
    """
    Submits the current URL to the webarchive and returns a job_id or completed archive
    """
    name = "wayback_enricher"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        assert type(self.secret) == str and len(self.secret) > 0, "please provide a value for the wayback_enricher API key"
        assert type(self.secret) == str and len(self.secret) > 0, "please provide a value for the wayback_enricher API secret"

    @staticmethod
    def configs() -> dict:
        return {
            "timeout": {"default": 5, "help": "number of seconds to wait for a response from webarchive's wayback machine, after that only job_id is saved but page will still be processed."},
            "key": {"default": None, "help": "wayback API key. to get credentials visit https://archive.org/account/s3.php"},
            "secret": {"default": None, "help": "wayback API secret. to get credentials visit https://archive.org/account/s3.php"}
        }

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"Enriching wayback for {url=}")

        ia_headers = {
            "Accept": "application/json",
            "Authorization": f"LOW {self.key}:{self.secret}"
        }
        r = requests.post('https://web.archive.org/save/', headers=ia_headers, data={'url': url})

        if r.status_code != 200:
            logger.error(em:=f"Internet archive failed with status of {r.status_code}: {r.json()}")
            to_enrich.set("wayback", em)
            return

        # check job status
        job_id = r.json()['job_id']

        # waits at most timeout seconds until job is completed, otherwise only enriches the job_id information
        start_time = time.time()
        wayback_url = False
        attempt = 1
        while not wayback_url and time.time() - start_time <= self.timeout:
            try:

                logger.debug(f"GETting status for {job_id=} on {url=} ({attempt=})")
                r_status = requests.get(f'https://web.archive.org/save/status/{job_id}', headers=ia_headers)
                r_json = r_status.json()
                if r_status.status_code == 200 and r_json['status'] == 'success':
                    wayback_url = f"https://web.archive.org/web/{r_json['timestamp']}/{r_json['original_url']}"
            except Exception as e:
                logger.warning(f"error fetching status for {url=} due to: {e}")
            if not wayback_url:
                attempt += 1
                time.sleep(1)  # TODO: can be improved with exponential backoff

        if wayback_url:
            to_enrich.set("wayback", wayback_url)
        else:
            to_enrich.set("wayback", {"job_id": job_id, "check_status": f'https://web.archive.org/save/status/{job_id}'})
