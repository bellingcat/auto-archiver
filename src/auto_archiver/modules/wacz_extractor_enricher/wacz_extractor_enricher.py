import jsonlines
import mimetypes
import os
import shutil
import subprocess
from zipfile import ZipFile
from loguru import logger
from warcio.archiveiterator import ArchiveIterator

from auto_archiver.core import Media, Metadata
from auto_archiver.core import Extractor, Enricher
from auto_archiver.utils import url as UrlUtil, random_str


class WaczExtractorEnricher(Enricher, Extractor):
    """
    Uses https://github.com/webrecorder/browsertrix-crawler to generate a .WACZ archive of the URL
    If used with [profiles](https://github.com/webrecorder/browsertrix-crawler#creating-and-using-browser-profiles)
    it can become quite powerful for archiving private content.
    When used as an archiver it will extract the media from the .WACZ archive so it can be enriched.
    """

    def setup(self) -> None:
        self.use_docker = os.environ.get("WACZ_ENABLE_DOCKER") or not os.environ.get("RUNNING_IN_DOCKER")
        self.docker_in_docker = os.environ.get("WACZ_ENABLE_DOCKER") and os.environ.get("RUNNING_IN_DOCKER")

        self.crawl_id = random_str(8)
        self.cwd_dind = f"/crawls/crawls{self.crawl_id}"
        self.browsertrix_home_host = os.environ.get("BROWSERTRIX_HOME_HOST")
        self.browsertrix_home_container = os.environ.get("BROWSERTRIX_HOME_CONTAINER") or self.browsertrix_home_host
        # create crawls folder if not exists, so it can be safely removed in cleanup
        if self.docker_in_docker:
            os.makedirs(self.cwd_dind, exist_ok=True)

    def cleanup(self) -> None:
        if self.docker_in_docker:
            logger.debug(f"Removing {self.cwd_dind=}")
            shutil.rmtree(self.cwd_dind, ignore_errors=True)

    def download(self, item: Metadata) -> Metadata:
        # this new Metadata object is required to avoid duplication
        result = Metadata()
        result.merge(item)
        if self.enrich(result):
            return result.success("wacz")

    def enrich(self, to_enrich: Metadata) -> bool:
        if to_enrich.get_media_by_id("browsertrix"):
            logger.info(f"WACZ enricher had already been executed: {to_enrich.get_media_by_id('browsertrix')}")
            return True

        url = to_enrich.get_url()

        collection = self.crawl_id
        browsertrix_home_host = self.browsertrix_home_host or os.path.abspath(self.tmp_dir)
        browsertrix_home_container = self.browsertrix_home_container or browsertrix_home_host

        cmd = [
            "crawl",
            "--url",
            url,
            "--scopeType",
            "page",
            "--generateWACZ",
            "--text",
            "to-pages",
            "--screenshot",
            "fullPage",
            "--collection",
            collection,
            "--id",
            collection,
            "--saveState",
            "never",
            "--behaviors",
            "autoscroll,autoplay,autofetch,siteSpecific",
            "--behaviorTimeout",
            str(self.timeout),
            "--timeout",
            str(self.timeout),
            "--diskUtilization",
            "99",
            # "--blockAds" # note: this has been known to cause issues on cloudflare protected sites
        ]

        if self.docker_in_docker:
            cmd.extend(["--cwd", self.cwd_dind])

        if self.auth_for_site(url):
            # there's an auth for this site, but browsertrix only supports username/password auth
            logger.warning(
                "The WACZ enricher / Browsertrix does not support using the 'authentication' information for logging in. You should consider creating a Browser Profile for WACZ archiving. More information: https://auto-archiver.readthedocs.io/en/latest/modules/autogen/extractor/wacz_extractor_enricher.html#browsertrix-profiles"
            )

        # call docker if explicitly enabled or we are running on the host (not in docker)
        if self.use_docker:
            logger.debug(f"generating WACZ in Docker for {url=}")
            logger.debug(f"{browsertrix_home_host=} {browsertrix_home_container=}")
            if self.docker_commands:
                cmd = self.docker_commands + cmd
            else:
                cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{browsertrix_home_host}:/crawls/",
                    "webrecorder/browsertrix-crawler",
                ] + cmd

            if self.profile:
                profile_file = f"profile-{self.crawl_id}.tar.gz"
                profile_fn = os.path.join(browsertrix_home_container, profile_file)
                logger.debug(f"copying {self.profile} to {profile_fn}")
                shutil.copyfile(self.profile, profile_fn)
                cmd.extend(["--profile", os.path.join("/crawls", profile_file)])

        else:
            logger.debug(f"generating WACZ without Docker for {url=}")

            if self.profile:
                cmd.extend(["--profile", os.path.join("/app", str(self.profile))])

        try:
            logger.info(f"Running browsertrix-crawler: {' '.join(cmd)}")
            my_env = os.environ.copy()
            if self.proxy_server:
                logger.debug("Using PROXY_SERVER proxy for browsertrix-crawler")
                my_env["PROXY_SERVER"] = self.proxy_server
            elif self.socks_proxy_host and self.socks_proxy_port:
                logger.debug("Using SOCKS proxy for browsertrix-crawler")
                my_env["SOCKS_HOST"] = self.socks_proxy_host
                my_env["SOCKS_PORT"] = str(self.socks_proxy_port)
            subprocess.run(cmd, check=True, env=my_env)
        except Exception as e:
            logger.error(f"WACZ generation failed: {e}")
            return False

        if self.docker_in_docker:
            wacz_fn = os.path.join(self.cwd_dind, "collections", collection, f"{collection}.wacz")
        elif self.use_docker:
            wacz_fn = os.path.join(browsertrix_home_container, "collections", collection, f"{collection}.wacz")
        else:
            wacz_fn = os.path.join("collections", collection, f"{collection}.wacz")

        if not os.path.exists(wacz_fn):
            logger.warning(f"Unable to locate and upload WACZ  {wacz_fn=}")
            return False

        to_enrich.add_media(Media(wacz_fn), "browsertrix")
        if self.extract_media or self.extract_screenshot:
            self.extract_media_from_wacz(to_enrich, wacz_fn)

        if self.docker_in_docker:
            jsonl_fn = os.path.join(self.cwd_dind, "collections", collection, "pages", "pages.jsonl")
        elif self.use_docker:
            jsonl_fn = os.path.join(browsertrix_home_container, "collections", collection, "pages", "pages.jsonl")
        else:
            jsonl_fn = os.path.join("collections", collection, "pages", "pages.jsonl")

        if not os.path.exists(jsonl_fn):
            logger.warning(f"Unable to locate and pages.jsonl  {jsonl_fn=}")
        else:
            logger.info(f"Parsing pages.jsonl  {jsonl_fn=}")
            with jsonlines.open(jsonl_fn) as reader:
                for obj in reader:
                    if "title" in obj:
                        to_enrich.set_title(obj["title"])
                    if "text" in obj:
                        to_enrich.set_content(obj["text"])

        return True

    def extract_media_from_wacz(self, to_enrich: Metadata, wacz_filename: str) -> None:
        """
        Receives a .wacz archive, and extracts all relevant media from it, adding them to to_enrich.
        """
        logger.info(f"WACZ extract_media or extract_screenshot flag is set, extracting media from {wacz_filename=}")

        # unzipping the .wacz
        tmp_dir = self.tmp_dir
        unzipped_dir = os.path.join(tmp_dir, "unzipped")
        with ZipFile(wacz_filename, "r") as z_obj:
            z_obj.extractall(path=unzipped_dir)

        # if warc is split into multiple gzip chunks, merge those
        warc_dir = os.path.join(unzipped_dir, "archive")
        warc_filename = os.path.join(tmp_dir, "merged.warc")
        with open(warc_filename, "wb") as outfile:
            for filename in sorted(os.listdir(warc_dir)):
                if filename.endswith(".gz"):
                    chunk_file = os.path.join(warc_dir, filename)
                    with open(chunk_file, "rb") as infile:
                        shutil.copyfileobj(infile, outfile)

        # get media out of .warc
        counter = 0
        seen_urls = set()

        with open(warc_filename, "rb") as warc_stream:
            for record in ArchiveIterator(warc_stream):
                # only include fetched resources
                if (
                    record.rec_type == "resource" and record.content_type == "image/png" and self.extract_screenshot
                ):  # screenshots
                    fn = os.path.join(tmp_dir, f"warc-file-{counter}.png")
                    with open(fn, "wb") as outf:
                        outf.write(record.raw_stream.read())
                    m = Media(filename=fn)
                    to_enrich.add_media(m, "browsertrix-screenshot")
                    counter += 1
                if not self.extract_media:
                    continue

                if record.rec_type != "response":
                    continue
                record_url = record.rec_headers.get_header("WARC-Target-URI")
                if not UrlUtil.is_relevant_url(record_url):
                    logger.debug(f"Skipping irrelevant URL {record_url} but it's still present in the WACZ.")
                    continue
                if record_url in seen_urls:
                    logger.debug(f"Skipping already seen URL {record_url}.")
                    continue

                # filter by media mimetypes
                content_type = record.http_headers.get("Content-Type")
                if not content_type:
                    continue
                if not any(x in content_type for x in ["video", "image", "audio"]):
                    continue

                # create local file and add media
                ext = mimetypes.guess_extension(content_type)
                warc_fn = f"warc-file-{counter}{ext}"
                fn = os.path.join(tmp_dir, warc_fn)

                record_url_best_qual = UrlUtil.twitter_best_quality_url(record_url)
                with open(fn, "wb") as outf:
                    outf.write(record.raw_stream.read())

                m = Media(filename=fn)
                m.set("src", record_url)
                # if a link with better quality exists, try to download that
                if record_url_best_qual != record_url:
                    try:
                        m.filename = self.download_from_url(record_url_best_qual, warc_fn)
                        m.set("src", record_url_best_qual)
                        m.set("src_alternative", record_url)
                    except Exception as e:
                        logger.warning(
                            f"Unable to download best quality URL for {record_url=} got error {e}, using original in WARC."
                        )

                # remove bad videos
                if m.is_video() and not m.is_valid_video():
                    continue

                to_enrich.add_media(m, warc_fn)
                counter += 1
                seen_urls.add(record_url)
        logger.info(f"WACZ extract_media/extract_screenshot finished, found {counter} relevant media file(s)")
