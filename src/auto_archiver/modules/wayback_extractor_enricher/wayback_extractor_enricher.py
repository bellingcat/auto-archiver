import json
from loguru import logger
import time
import requests

from auto_archiver.core import Extractor, Enricher
from auto_archiver.utils import url as UrlUtil
from auto_archiver.core import Metadata


class WaybackExtractorEnricher(Enricher, Extractor):
    """
    Submits the current URL to the webarchive and returns a job_id or completed archive.

    The Wayback machine will rate-limit IP heavy usage.
    """

    def download(self, item: Metadata) -> Metadata:
        # this new Metadata object is required to avoid duplication
        result = Metadata()
        result.merge(item)
        if self.enrich(result):
            return result.success("wayback")

    def enrich(self, to_enrich: Metadata) -> bool:
        proxies = {}
        if self.proxy_http:
            proxies["http"] = self.proxy_http
        if self.proxy_https:
            proxies["https"] = self.proxy_https

        url = to_enrich.get_url()
        if UrlUtil.is_auth_wall(url):
            logger.debug(f"[SKIP] WAYBACK since url is behind AUTH WALL: {url=}")
            return

        logger.debug(f"calling wayback for {url=}")

        if to_enrich.get("wayback"):
            logger.info(f"Wayback enricher had already been executed: {to_enrich.get('wayback')}")
            return True

        ia_headers = {"Accept": "application/json", "Authorization": f"LOW {self.key}:{self.secret}"}
        post_data = {"url": url}
        if self.if_not_archived_within:
            post_data["if_not_archived_within"] = self.if_not_archived_within
        # see https://docs.google.com/document/d/1Nsv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA for more options
        r = requests.post("https://web.archive.org/save/", headers=ia_headers, data=post_data, proxies=proxies)

        if r.status_code != 200:
            logger.error(em := f"Internet archive failed with status of {r.status_code}: {r.json()}")
            to_enrich.set("wayback", em)
            return False

        # check job status
        try:
            job_id = r.json().get("job_id")
            if not job_id:
                logger.error(f"Wayback failed with {r.json()}")
                return False
        except json.decoder.JSONDecodeError:
            logger.error(f"Expected a JSON with job_id from Wayback and got {r.text}")
            return False

        # waits at most timeout seconds until job is completed, otherwise only enriches the job_id information
        start_time = time.time()
        wayback_url = False
        attempt = 1
        while not wayback_url and time.time() - start_time <= self.timeout:
            try:
                logger.debug(f"GETting status for {job_id=} on {url=} ({attempt=})")
                r_status = requests.get(
                    f"https://web.archive.org/save/status/{job_id}", headers=ia_headers, proxies=proxies
                )
                r_json = r_status.json()
                if r_status.status_code == 200 and r_json["status"] == "success":
                    wayback_url = f"https://web.archive.org/web/{r_json['timestamp']}/{r_json['original_url']}"
                elif r_status.status_code != 200 or r_json["status"] != "pending":
                    logger.error(f"Wayback failed with {r_json}")
                    return False
            except requests.exceptions.RequestException as e:
                logger.warning(f"RequestException: fetching status for {url=} due to: {e}")
                break
            except json.decoder.JSONDecodeError:
                logger.error(f"Expected a JSON from Wayback and got {r.text} for {url=}")
                break
            except Exception as e:
                logger.warning(f"error fetching status for {url=} due to: {e}")
            if not wayback_url:
                attempt += 1
                time.sleep(1)  # TODO: can be improved with exponential backoff

        if wayback_url:
            to_enrich.set("wayback", wayback_url)
        else:
            to_enrich.set(
                "wayback", {"job_id": job_id, "check_status": f"https://web.archive.org/save/status/{job_id}"}
            )
        to_enrich.set("check wayback", f"https://web.archive.org/web/*/{url}")
        return True
