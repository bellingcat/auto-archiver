import time
import re

import requests
from bs4 import BeautifulSoup
from seleniumbase import SB
from auto_archiver.utils.custom_logger import logger
from auto_archiver.utils import url as UrlUtil
from auto_archiver.core import Enricher, Metadata


class GhostarchiveEnricher(Enricher):
    """
    Submits the current URL to Ghost Archive (ghostarchive.org) for archiving
    and stores the archived page URL as enrichment metadata.

    Ghost Archive has no official API — this module interacts with the web form
    and parses HTML responses. The submission endpoint is protected by Cloudflare,
    so a headless browser (SeleniumBase) is used for archival submissions, while
    plain HTTP requests are used for searching existing archives.

    Note: this module only confirms that Ghost Archive accepted the submission
    and returned an archive URL. It does not verify that the archived page
    content is complete or correctly rendered.
    """

    GHOSTARCHIVE_BASE = "https://ghostarchive.org"
    ARCHIVE_ENDPOINT = f"{GHOSTARCHIVE_BASE}/archive2"
    SEARCH_ENDPOINT = f"{GHOSTARCHIVE_BASE}/search"
    ARCHIVE_URL_PATTERN = re.compile(r"/archive/([A-Za-z0-9]+)")

    def _get_proxies(self) -> dict:
        proxies = {}
        if self.proxy_http:
            proxies["http"] = self.proxy_http
        if self.proxy_https:
            proxies["https"] = self.proxy_https
        return proxies

    def _get_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    def _normalize_archive_href(self, href: str) -> str | None:
        """Normalize an archive link href to a full HTTPS URL, filtering out replay links."""
        if "/archive/" not in href or "/replay/" in href:
            return None
        if href.startswith("/"):
            return f"{self.GHOSTARCHIVE_BASE}{href}"
        if href.startswith("http://ghostarchive.org"):
            return href.replace("http://", "https://")
        if href.startswith("https://ghostarchive.org"):
            return href
        return None

    def _search_existing(self, url: str) -> str | None:
        """
        Search Ghost Archive for an existing archive of the given URL.
        Returns the archive URL if found, otherwise None.
        """
        try:
            r = requests.get(
                self.SEARCH_ENDPOINT,
                params={"term": url},
                headers=self._get_headers(),
                proxies=self._get_proxies(),
                timeout=30,
            )
            if r.status_code != 200:
                logger.warning(f"Ghost Archive search returned status {r.status_code}")
                return None

            soup = BeautifulSoup(r.text, "html.parser")
            for link in soup.find_all("a", href=True):
                archive_url = self._normalize_archive_href(link["href"])
                if archive_url:
                    logger.info(f"Found existing Ghost Archive: {archive_url}")
                    return archive_url

        except requests.exceptions.RequestException as e:
            logger.warning(f"Ghost Archive search failed: {e}")

        return None

    def _submit_url(self, url: str) -> str | None:
        """
        Submit a URL to Ghost Archive for archiving using a headless browser.
        The /archive2 endpoint is Cloudflare-protected, requiring JS execution.
        Returns the archive URL if successful, otherwise None.
        """
        try:
            with SB(uc=True, headless=True) as sb:
                logger.debug("Opening Ghost Archive homepage in headless browser")
                sb.open(self.GHOSTARCHIVE_BASE)

                # fill in the archive form and submit
                sb.type('input[name="archive"]', url)
                sb.click('input[type="submit"][value="Submit for archival"]')

                # wait for navigation to /archive/{id} or timeout
                start_time = time.time()
                while time.time() - start_time < self.timeout:
                    current_url = sb.get_current_url()
                    if self.ARCHIVE_URL_PATTERN.search(current_url):
                        archive_url = current_url.split("?")[0]
                        logger.info(f"Ghost Archive saved: {archive_url}")
                        return archive_url
                    time.sleep(2)

                # if we didn't redirect, try parsing the page source
                page_source = sb.get_page_source()
                return self._parse_archive_url(page_source)

        except Exception as e:
            logger.warning(f"Ghost Archive submission failed: {e}")
            return None

    def _parse_archive_url(self, html: str) -> str | None:
        """Parse HTML response to find an archive URL."""
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a", href=True):
            archive_url = self._normalize_archive_href(link["href"])
            if archive_url:
                return archive_url
        return None

    def enrich(self, to_enrich: Metadata) -> bool:
        url = to_enrich.get_url()
        if UrlUtil.is_auth_wall(url):
            logger.debug("[SKIP] Ghost Archive since url is behind AUTH WALL")
            return False

        if to_enrich.get("ghostarchive"):
            logger.info(f"Ghost Archive enricher had already been executed: {to_enrich.get('ghostarchive')}")
            return True

        # optionally check for existing archive first
        archive_url = None
        if self.check_existing:
            logger.debug(f"Searching Ghost Archive for existing archive of {url}")
            archive_url = self._search_existing(url)

        if not archive_url:
            logger.debug(f"Submitting {url} to Ghost Archive")
            archive_url = self._submit_url(url)

        if archive_url:
            to_enrich.set("ghostarchive", archive_url)
            return True

        logger.warning(f"Ghost Archive failed to archive {url}")
        return False
