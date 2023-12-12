import jsonlines
import mimetypes
import os, shutil, subprocess
from zipfile import ZipFile
from loguru import logger
from warcio.archiveiterator import ArchiveIterator

from ..core import Media, Metadata, ArchivingContext
from . import Enricher
from ..archivers import Archiver
from ..utils import UrlUtil, random_str


class WaczArchiverEnricher(Enricher, Archiver):
    """
    Uses https://github.com/webrecorder/browsertrix-crawler to generate a .WACZ archive of the URL
    If used with [profiles](https://github.com/webrecorder/browsertrix-crawler#creating-and-using-browser-profiles)
    it can become quite powerful for archiving private content.
    When used as an archiver it will extract the media from the .WACZ archive so it can be enriched.
    """
    name = "wacz_archiver_enricher"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {
            "profile": {"default": None, "help": "browsertrix-profile (for profile generation see https://github.com/webrecorder/browsertrix-crawler#creating-and-using-browser-profiles)."},
            "docker_commands": {"default": None, "help":"if a custom docker invocation is needed"},
            "timeout": {"default": 120, "help": "timeout for WACZ generation in seconds"},
            "extract_media": {"default": True, "help": "If enabled all the images/videos/audio present in the WACZ archive will be extracted into separate Media. The .wacz file will be kept untouched."}
        }

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

        collection = random_str(8)
        browsertrix_home_host = os.environ.get('BROWSERTRIX_HOME_HOST') or os.path.abspath(ArchivingContext.get_tmp_dir())
        browsertrix_home_container = os.environ.get('BROWSERTRIX_HOME_CONTAINER') or browsertrix_home_host

        cmd = [
            "crawl",
            "--url", url,
            "--scopeType", "page",
            "--generateWACZ",
            "--text",
            "--screenshot", "fullPage",
            "--collection", collection,
            "--id", collection,
            "--saveState", "never",
            "--behaviors", "autoscroll,autoplay,autofetch,siteSpecific",
            "--behaviorTimeout", str(self.timeout),
            "--timeout", str(self.timeout)]

        # call docker if explicitly enabled or we are running on the host (not in docker)
        use_docker = os.environ.get('WACZ_ENABLE_DOCKER') or not os.environ.get('RUNNING_IN_DOCKER')

        if use_docker:
            logger.debug(f"generating WACZ in Docker for {url=}")
            logger.debug(f"{browsertrix_home_host=} {browsertrix_home_container=}")
            if self.docker_commands:
                cmd = self.docker_commands + cmd
            else:
                cmd = ["docker", "run", "--rm", "-v", f"{browsertrix_home_host}:/crawls/", "webrecorder/browsertrix-crawler"] + cmd

            if self.profile:
                profile_fn = os.path.join(browsertrix_home_container, "profile.tar.gz")
                logger.debug(f"copying {self.profile} to {profile_fn}")
                shutil.copyfile(self.profile, profile_fn)
                cmd.extend(["--profile", os.path.join("/crawls", "profile.tar.gz")])

        else:
            logger.debug(f"generating WACZ without Docker for {url=}")

            if self.profile:
                cmd.extend(["--profile", os.path.join("/app", str(self.profile))])

        try:
            logger.info(f"Running browsertrix-crawler: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
        except Exception as e:
            logger.error(f"WACZ generation failed: {e}")
            return False

        if use_docker:
            wacz_fn = os.path.join(browsertrix_home_container, "collections", collection, f"{collection}.wacz")
        else:
            wacz_fn = os.path.join("collections", collection, f"{collection}.wacz")

        if not os.path.exists(wacz_fn):
            logger.warning(f"Unable to locate and upload WACZ  {wacz_fn=}")
            return False

        to_enrich.add_media(Media(wacz_fn), "browsertrix")
        if self.extract_media:
            self.extract_media_from_wacz(to_enrich, wacz_fn)

        if use_docker:
            jsonl_fn = os.path.join(browsertrix_home_container, "collections", collection, "pages", "pages.jsonl")
        else:
            jsonl_fn = os.path.join("collections", collection, "pages", "pages.jsonl")

        if not os.path.exists(jsonl_fn):
            logger.warning(f"Unable to locate and pages.jsonl  {jsonl_fn=}")
        else:
            logger.info(f"Parsing pages.jsonl  {jsonl_fn=}")
            with jsonlines.open(jsonl_fn) as reader:
                for obj in reader:
                    if 'title' in obj:
                        to_enrich.set_title(obj['title'])
                    if 'text' in obj:
                        to_enrich.set_content(obj['text'])


        return True

    def extract_media_from_wacz(self, to_enrich: Metadata, wacz_filename: str) -> None:
        """
        Receives a .wacz archive, and extracts all relevant media from it, adding them to to_enrich.
        """
        logger.info(f"WACZ extract_media flag is set, extracting media from {wacz_filename=}")

        # unzipping the .wacz
        tmp_dir = ArchivingContext.get_tmp_dir()
        unzipped_dir = os.path.join(tmp_dir, "unzipped")
        with ZipFile(wacz_filename, 'r') as z_obj:
            z_obj.extractall(path=unzipped_dir)

        # if warc is split into multiple gzip chunks, merge those
        warc_dir = os.path.join(unzipped_dir, "archive")
        warc_filename = os.path.join(tmp_dir, "merged.warc")
        with open(warc_filename, 'wb') as outfile:
            for filename in sorted(os.listdir(warc_dir)):
                if filename.endswith('.gz'):
                    chunk_file = os.path.join(warc_dir, filename)
                    with open(chunk_file, 'rb') as infile:
                        shutil.copyfileobj(infile, outfile)

        # get media out of .warc
        counter = 0
        seen_urls = set()
        with open(warc_filename, 'rb') as warc_stream:
            for record in ArchiveIterator(warc_stream):
                # only include fetched resources
                if record.rec_type == "resource":  # screenshots
                    fn = os.path.join(tmp_dir, f"warc-file-{counter}.png")
                    with open(fn, "wb") as outf: outf.write(record.raw_stream.read())
                    m = Media(filename=fn)
                    to_enrich.add_media(m, "browsertrix-screenshot")
                    counter += 1

                if record.rec_type != 'response': continue
                record_url = record.rec_headers.get_header('WARC-Target-URI')
                if not UrlUtil.is_relevant_url(record_url):
                    logger.debug(f"Skipping irrelevant URL {record_url} but it's still present in the WACZ.")
                    continue
                if record_url in seen_urls:
                    logger.debug(f"Skipping already seen URL {record_url}.")
                    continue

                # filter by media mimetypes
                content_type = record.http_headers.get("Content-Type")
                if not content_type: continue
                if not any(x in content_type for x in ["video", "image", "audio"]): continue

                # create local file and add media
                ext = mimetypes.guess_extension(content_type)
                warc_fn = f"warc-file-{counter}{ext}"
                fn = os.path.join(tmp_dir, warc_fn)

                record_url_best_qual = UrlUtil.twitter_best_quality_url(record_url)
                with open(fn, "wb") as outf: outf.write(record.raw_stream.read())

                m = Media(filename=fn)
                m.set("src", record_url)
                # if a link with better quality exists, try to download that
                if record_url_best_qual != record_url:
                    try:
                        m.filename = self.download_from_url(record_url_best_qual, warc_fn, to_enrich)
                        m.set("src", record_url_best_qual)
                        m.set("src_alternative", record_url)
                    except Exception as e: logger.warning(f"Unable to download best quality URL for {record_url=} got error {e}, using original in WARC.")

                # remove bad videos
                if m.is_video() and not m.is_valid_video(): continue
                
                to_enrich.add_media(m, warc_fn)
                counter += 1
                seen_urls.add(record_url)
        logger.info(f"WACZ extract_media finished, found {counter} relevant media file(s)")
