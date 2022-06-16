import time, requests

from loguru import logger
from bs4 import BeautifulSoup

from storages import Storage
from .base_archiver import Archiver, ArchiveResult
from configs import WaybackConfig


class WaybackArchiver(Archiver):
    """
    This archiver could implement a check_if_exists by going to "https://web.archive.org/web/{url}"
    but that might not be desirable since the webpage might have been archived a long time ago and thus have changed
    """
    name = "wayback"

    def __init__(self, storage: Storage, driver, config: WaybackConfig):
        super(WaybackArchiver, self).__init__(storage, driver)
        self.config = config
        self.seen_urls = {}

    def download(self, url, check_if_exists=False):
        if self.config is None:
            logger.error('Missing Wayback config')
            return False
        if check_if_exists:
            if url in self.seen_urls: return self.seen_urls[url]

        screenshot = self.get_screenshot(url)
        logger.debug(f"POSTing {url=} to web.archive.org")
        ia_headers = {
            "Accept": "application/json",
            "Authorization": f"LOW {self.config.key}:{self.config.secret}"
        }
        r = requests.post('https://web.archive.org/save/', headers=ia_headers, data={'url': url})

        if r.status_code != 200:
            logger.warning(f"Internet archive failed with status of {r.status_code}")
            return ArchiveResult(status="Internet archive failed", screenshot=screenshot)

        if 'job_id' not in r.json() and 'message' in r.json():
            return self.custom_retry(r.json(), screenshot=screenshot)

        job_id = r.json()['job_id']
        logger.debug(f"GETting status for {job_id=} on {url=}")
        status_r = requests.get(f'https://web.archive.org/save/status/{job_id}', headers=ia_headers)
        retries = 0

        # TODO: make the job queue parallel -> consider propagation of results back to sheet though
        # wait 90-120 seconds for the archive job to finish
        while (status_r.status_code != 200 or status_r.json()['status'] == 'pending') and retries < 30:
            time.sleep(3)
            try:
                logger.debug(f"GETting status for {job_id=} on {url=} [{retries=}]")
                status_r = requests.get(f'https://web.archive.org/save/status/{job_id}', headers=ia_headers)
            except:
                time.sleep(1)
            retries += 1

        if status_r.status_code != 200:
            return ArchiveResult(status=f"Internet archive failed: check https://web.archive.org/save/status/{job_id}", screenshot=screenshot)

        status_json = status_r.json()
        if status_json['status'] != 'success':
            return self.custom_retry(status_json, screenshot=screenshot)

        archive_url = f"https://web.archive.org/web/{status_json['timestamp']}/{status_json['original_url']}"

        try:
            req = requests.get(archive_url)
            parsed = BeautifulSoup(req.content, 'html.parser')
            title = parsed.find_all('title')[0].text
            if title == 'Wayback Machine':
                title = 'Could not get title'
        except:
            title = "Could not get title"
        screenshot = self.get_screenshot(url)
        self.seen_urls[url] = ArchiveResult(status='success', cdn_url=archive_url, title=title, screenshot=screenshot)
        return self.seen_urls[url]

    def custom_retry(self, json_data, **kwargs):
        logger.warning(f"Internet archive failed json \n {json_data}")
        if "please try again" in str(json_data).lower():
            return self.signal_retry_in(**kwargs)
        if "this host has been already captured" in str(json_data).lower():
            return self.signal_retry_in(**kwargs, min_seconds=86400, max_seconds=129600)  # 24h to 36h later
        return ArchiveResult(status=f"Internet archive failed: {json_data}", **kwargs)
