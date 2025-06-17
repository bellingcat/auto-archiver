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

        logger.debug(f"POSTing to wayback /save for {url=}")

        if to_enrich.get("wayback"):
            logger.info(f"Wayback enricher had already been executed: {to_enrich.get('wayback')}")
            return True

        ia_headers = {"Accept": "application/json", "Authorization": f"LOW {self.key}:{self.secret}"}
        post_data = {"url": url}
        if self.if_not_archived_within:
            post_data["if_not_archived_within"] = self.if_not_archived_within
        # see https://docs.google.com/document/d/1Nsv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA for more options
        # DM 4th Jun 25 - the post timeout will be 4:35 with 10 attempts.
        # we need this to be successful as need the job_id to check the status to put in the metadata.
        attempt = 1
        success = False
        while attempt <= 10:
            try:
                r = requests.post("https://web.archive.org/save/", headers=ia_headers, data=post_data, proxies=proxies)
                success = True
            except Exception as e:
                # DM 3rd Jun 25 - max retries exceeded with url: /save/ catch
                logger.warning(f"Problem posting to wayback - retrying {attempt} error - {e}")
                time.sleep(5 * attempt) # linear backoff
                attempt += 1
            if success:
                break # out of while loop

        if not success:
            logger.error(f"Error calling Wayback - given up after {attempt} attempts.")
            return False

        if r.status_code != 200:
            # DM 6th Jun 25 - this is a workaround for a wayback issue where it returned a non json response text 
            try:
                error_content = r.json()
            except requests.exceptions.JSONDecodeError:
                error_content = r.text
            logger.error(em := f"Internet archive failed with status of {r.status_code}: {error_content}")
            to_enrich.set("wayback", em)
            return False

        # check wayback job status
        try:
            job_id = r.json().get("job_id")
            if not job_id:
                # for some sites likes twitter, with 'we're facing some limitation' this is business as usual for us, so not an error
                if 'twitter.com' or 'x.com' in url:
                    logger.info(f"Wayback failed and we know about this with Twitter/X with {r.json()} - if it starts working from wayback side, this will be fine")
                    return False
                else:
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
                logger.info(f"Attempt {attempt} of fetching status for {url=} failed which is okay due to: {e}")
                logger.info(f"If after {self.timeout} seconds the wayback url is not found, then we will just put the check status link in the metadata")
                break
            except json.decoder.JSONDecodeError:
                logger.error(f"Expected a JSON from Wayback and got {r.text} for {url=}")
                break
            except Exception as e:
                logger.warning(f"error fetching status for {url=} due to: {e}")
            if not wayback_url:
                attempt += 1
                # if we try too many times here it will affect the next POST to wayback
                # which we really need to be successful.
                # for 30seconds timeout (in yaml) this gives 3 attempts
                time.sleep(5 * attempt)  # linear backoff. todo: exponential backoff

        if wayback_url:
            logger.info(f"Wayback GET status successful - {wayback_url=}")
            to_enrich.set("wayback", wayback_url)
        else:
            logger.info(f"Wayback GET status failed so reverting to check status link")
            to_enrich.set(
                "wayback", {"job_id": job_id, "check_status": f"https://web.archive.org/save/status/{job_id}"}
            )
        to_enrich.set("check wayback", f"https://web.archive.org/web/*/{url}")
        return True
