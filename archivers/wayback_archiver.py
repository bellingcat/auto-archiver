import time, requests

from loguru import logger
from bs4 import BeautifulSoup

from storages import Storage
from .base_archiver import Archiver, ArchiveResult
from configs import WaybackConfig


class WaybackArchiver(Archiver):
    name = "wayback"

    def __init__(self, storage: Storage, driver, config: WaybackConfig):
        super(WaybackArchiver, self).__init__(storage, driver)
        self.config = config
        # TODO: this logic should live at the auto-archiver level
        self.seen_urls = {}

    def download(self, url, check_if_exists=False):
        if check_if_exists:
            if url in self.seen_urls: return self.seen_urls[url]

            logger.debug(f"checking if {url=} already on archive.org")
            archive_url = f"https://web.archive.org/web/{url}"
            req = requests.get(archive_url)
            if req.status_code == 200:
                return self.if_archived_return_with_screenshot(url, archive_url, req=req, status='already archived')

        logger.debug(f"POSTing {url=} to web.archive.org")
        ia_headers = {
            "Accept": "application/json",
            "Authorization": f"LOW {self.config.key}:{self.config.secret}"
        }
        r = requests.post('https://web.archive.org/save/', headers=ia_headers, data={'url': url})

        if r.status_code != 200:
            logger.warning(f"Internet archive failed with status of {r.status_code}")
            return ArchiveResult(status="Internet archive failed")

        if 'job_id' not in r.json() and 'message' in r.json():
            logger.warning(f"Internet archive failed json \n {r.json()}")
            return ArchiveResult(status=f"Internet archive failed: {r.json()['message']}")

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
            return ArchiveResult(status="Internet archive failed")

        status_json = status_r.json()
        if status_json['status'] != 'success':
            if "please try again" in str(status_json).lower():
                return self.signal_retry_in()
            return ArchiveResult(status='Internet Archive failed: ' + str(status_json))

        archive_url = f"https://web.archive.org/web/{status_json['timestamp']}/{status_json['original_url']}"
        return self.if_archived_return_with_screenshot(archive_url)

    def if_archived_return_with_screenshot(self, url, archive_url, req=None, status='success'):
        try:
            if req is None:
                req = requests.get(archive_url)
            parsed = BeautifulSoup(req.content, 'html.parser')
            title = parsed.find_all('title')[0].text
            if title == 'Wayback Machine':
                title = 'Could not get title'
        except:
            title = "Could not get title"
        screenshot = self.get_screenshot(url)
        self.seen_urls[url] = ArchiveResult(status=status, cdn_url=archive_url, title=title, screenshot=screenshot)
        return self.seen_urls[url]
