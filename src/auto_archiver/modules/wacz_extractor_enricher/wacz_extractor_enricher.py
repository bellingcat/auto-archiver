import time
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

    Special case for facebook.com that 
    - gets high resolution images
    - crawls the images if a post contains multiple
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

        # If url ends with a # then remove it as otherwise browsertrix will fail
        # eg DM 13th Jun 25 - https://www.radiookapi.net/2025/06/12/actualite/securite/au-moins-35-civils-tues-dans-une-attaque-attribuee-aux-adf-banango#
        if url.endswith('#'):
            url = url[:-1]

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
            if (
                'facebook.com' in url or 
                'twitter.com' in url or 
                'x.com' in url or
                'instagram.com' in url
            ):
                logger.debug(f"Facebook, Twitter/X or Instagram - should be a loggedin secrets/profile.tar.gz. This is important for images and screenshot")
            else:
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

        # DM 11th Jun 25 - the call to extract_media_from_wacz
        # special case here for facebook.com
        if self.extract_media or self.extract_screenshot:
            if 'facebook.com/' in url:
                self.facebook_extract_media_from_wacz(to_enrich, wacz_fn, url)
            else:
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

    def facebook_extract_media_from_wacz(self, to_enrich: Metadata, wacz_filename: str, url: str) -> None:
        """
        Facebook specific extractor
        Receives a .wacz archive, and extracts all relevant media from it, adding them to to_enrich.
        Part 1 - extract images from the wacz. Only relevant for /photo (strategy 0) pages. This includes full resolution image so no need to crawl.
        Part 2 - 
        """
        logger.info(f"Facebook Part 1 - extracting media from {wacz_filename=}")

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
        counter_warc_files = 0
        counter_screenshots = 0
        seen_urls = set()

        # using a separate linux_tmp_dir for Part 2 to avoid confusion with the tmp_dir used for Part 1
        linux_tmp_dir = os.path.expanduser('~/aatmp')

        # Check if the directory exists, and if not, create it
        if os.path.exists(linux_tmp_dir):
           logger.debug(f"Part 2 - deleting all files in {linux_tmp_dir}")
           shutil.rmtree(linux_tmp_dir)
           os.makedirs(linux_tmp_dir)
        else:
            logger.debug(f"Part 2 - creating directory {linux_tmp_dir}")
            os.makedirs(linux_tmp_dir)

        # DM 13th Jun 2025
        # for strategy 1 - we need the most prevalent set_id
        # so we crawl the correct set as otherwise we may get wrong images
        with open(warc_filename, "rb") as warc_stream:
            list_of_set_ids = []
            for record in ArchiveIterator(warc_stream):
                if record.rec_type == "request": pass
                else: continue 

                uri = record.rec_headers.get_header('WARC-Target-URI')

                if "bulk-route-definitions/" in uri:
                    content = record.content_stream().read()
                    foo = str(content)
                    photo_string_start_pos = foo.find(f'photo%2F%3Ffbid%3D',0)

                    if (photo_string_start_pos > 0):
                        fbid_start_pos = photo_string_start_pos + 18
                        middle_26_start_pos = foo.find(f'%26', fbid_start_pos)
                        fb_id = foo[fbid_start_pos:middle_26_start_pos]
                        set_end_pos = foo.find(f'%26', middle_26_start_pos+1)
                        set_id = foo[middle_26_start_pos+13:set_end_pos]
                        logger.info(f" found {set_id=} in bulk-route-definitions and adding to list so can calculate most prevalent")
                        list_of_set_ids.append(set_id)

        if list_of_set_ids: pass
        else:
            logger.debug("No set_ids found in bulk-route-definitions in any record. Have seen this if content is not available ie page has been taken down")
            return

        # get the most prevalent set_id
        most_prevalent_set_id = max(set(list_of_set_ids), key=list_of_set_ids.count)
        logger.info(f" calculated: {most_prevalent_set_id=}")


        with open(warc_filename, "rb") as warc_stream:
            full_crawl_done = False
            for record in ArchiveIterator(warc_stream):
                # extract just the screenshot from the facebook page wacz
                if (record.rec_type == "resource" and record.content_type == "image/png" and self.extract_screenshot):
                    fn = os.path.join(tmp_dir, f"warc-file-{counter_screenshots}.png")
                    with open(fn, "wb") as outf:
                        outf.write(record.raw_stream.read())
                    m = Media(filename=fn)
                    to_enrich.add_media(m, f"browsertrix-screenshot-{counter_screenshots}")
                    logger.debug(f"Part 1 - Added Screenshot")
                    logger.debug(f"Part 1 - is a chance that will not be called browser-screenshot, as may have been added already, and will get deleted in deduplication.")
                    counter_screenshots += 1
                    
                # purely to make sure we get the screenshot
                if full_crawl_done: continue # to next record

                # continue to next if don't want media (essentially do nothing else but the screenshot above)
                if self.extract_media: pass
                else: continue

                # Strategy 0 - single image
                if "facebook.com/photo" in url:
                    # eg single lady
                    # https://www.facebook.com/khitthitnews/posts/pfbid0PTvT6iAccWqatvbDQNuqpFwL5WKzHuLK4QjP97Fwut637CV3XXQU53z1s2bJMAKwl
                    # logger.debug(f"Strategy 0 - this is a /photo page so the image will be at full resolution and don't need to crawl")
                    crawl_and_get_media_from_sub_page = False
                else:
                    # eg 3 images
                    # https://www.facebook.com/khitthitnews/posts/pfbid0PTvT6iAccWqatvbDQNuqpFwL5WKzHuLK4QjP97Fwut637CV3XXQU53z1s2bJMAKwl
                    # eg 15 images
                    # https://www.facebook.com/permalink.php?story_fbid=pfbid0BqNZHQaQfqTAKzVaaeeYNuyPXFJhkPmzwWT7mZPZJLFnHNEvsdbnLJRPkHJDMcqFl&id=100082135548177
                    crawl_and_get_media_from_sub_page = True

                if crawl_and_get_media_from_sub_page:
                    if record.rec_type == "request": pass
                    else: continue # to next record - we are only interested in the request at the moment to get the fb_id and set_id

                    # CRAWL START
                    # logger.debug(f"Strategy 1 + - crawling the sub page to get the media")

                    # Get fb_id and set_id
                    # strategy 1 - 3 images and want full resolution images
                    # https://www.facebook.com/khitthitnews/posts/pfbid0PTvT6iAccWqatvbDQNuqpFwL5WKzHuLK4QjP97Fwut637CV3XXQU53z1s2bJMAKwl

                    # writing in table image: 
                    # https://www.facebook.com/photo/?fbid=1646726009098072&set=pcb.1646726145764725
                    # fbid = 1646726009098072 

                    # set = 1646726145764725

                    # crosshairs image
                    # https://www.facebook.com/photo?fbid=1646726045764735&set=pcb.1646726145764725
                    # fbid = 1646726045764735
                    
                    # printout of map image
                    # https://www.facebook.com/photo?fbid=1646726095764730&set=pcb.1646726145764725
                    # fbid = 1646726095764730
                    
                    uri = record.rec_headers.get_header('WARC-Target-URI')

                    # There are many instances of this and it is possible to get the wrong one.
                    # DM 13th Jun 25 - we already know the most prevalent set_id that we want
                    if "bulk-route-definitions/" in uri:
                        content = record.content_stream().read()
                        foo = str(content)

                        # Strategy 1 - 3 images
                        # photo%2F%3Ffbid%3D1646726009098072%26set%3Dpcb.1646726145764725%26
                        # writing in table image 
                        # fbid = 1646726009098072
                        # set = pcb.1646726145764725
                        photo_string_start_pos = foo.find(f'photo%2F%3Ffbid%3D',0)

                        if (photo_string_start_pos > 0):
                            logger.debug("Part 1 - found photo string so get the fb_id and set_id so can request it to get full res image")
                            logger.debug("   and then the next fb_id from the carousel")
                            fbid_start_pos = photo_string_start_pos + 18

                            middle_26_start_pos = foo.find(f'%26', fbid_start_pos)

                            fb_id = foo[fbid_start_pos:middle_26_start_pos]
                            # # photo%2F%3Ffbid%3D1646726009098072%26set%3Dpcb.1646726145764725%26
                            set_end_pos = foo.find(f'%26', middle_26_start_pos+1)

                            set_id = foo[middle_26_start_pos+13:set_end_pos]

                            if set_id == most_prevalent_set_id: pass
                            else:
                                logger.info(f"Part 1 - skipping set_id {set_id=} as not the most prevalent set_id {most_prevalent_set_id=}")
                                continue # to next record

                            logger.info(f"  *** Part 1 - Strategy 1 {fb_id=} and {set_id=}")
                            # bar = f'https://www.facebook.com/photo/?fbid={fb_id}&set=pcb.{set_id}'

                            # Part 2
                            fb_ids_to_request = []
                            fb_ids_requested = []
                            while (True):
                                builder_url = f"https://www.facebook.com/photo?fbid={fb_id}&set=pcb.{set_id}"

                                fb_ids_requested.append(fb_id)

                                logger.info(f"  *** Part 2 next trying url for js page {builder_url}")

                                # next_fb_id = self.save_images_to_enrich_object_from_url_using_browsertrix(builder_url, to_enrich, fb_id)
                                list_of_next_fb_ids = self.save_images_to_enrich_object_from_url_using_browsertrix(builder_url, to_enrich, fb_id)

                                # iterate over list_of_next_fb_ids and add to fb_ids_to_request if not in fb_ids_requested
                                for next_fb_id in list_of_next_fb_ids:
                                    if next_fb_id not in fb_ids_requested:
                                        fb_ids_to_request.append(next_fb_id)

                                logger.debug(f"Part 2 - fb_ids_to_request {len(fb_ids_to_request)}")
                                logger.debug(f"Part 2 - fb_ids_requested {len(fb_ids_requested)}")

                                if len(fb_ids_to_request) == 0:
                                    logger.debug(f"Part 2 - no more fb_ids to request so end")
                                    break # out of while

                                fb_id = fb_ids_to_request.pop(0)

                                # iterate over fb_ids_to_request and request the url

                                total_images = len(to_enrich.media)
                                logger.debug(f"Part 2 - total_images {total_images} - includes duplicates")
                                if total_images > 90:
                                    logger.warning('Total images is > max so stopping crawl')
                                    break # out of while
                                
                            if len(fb_ids_requested) == 1:
                                logger.debug("Probably the wrong fb_id url here in Part 2, as only 1 fb_ids_requested")
                                logger.debug("so not the carousel we want")
                                logger.debug("continuing to next record in root url (Part 1) ")
                                continue # to next record

                            logger.debug(f"Part 2 END of while loop")
                            # we can't return here as the screenshot may not have been added yet

                            full_crawl_done = True
                            # return
                        else:
                            # logger.debug('photo string not found in bulk-route-definitions - this is normal. 1 out of 3 have seen work... ')
                            # logger.debug('it also could be a single image which is different')
                            ## TODO - strategy x
                            continue # to next record

                    # END of if crawl_and_get_media_from_sub_page
                    continue # onto the next record

                # if part 2 crawler has happened then we don't want to do anything else
                # but we do want to iterate over all records so that the screenshot is added
                if crawl_and_get_media_from_sub_page: continue # to next record
                else: pass

                # Only part 1 - strategy 0 code below
                # if record.rec_type != "response": continue
                if record.rec_type == "response": pass
                else: continue

                # so response has this header!
                record_url = record.rec_headers.get_header("WARC-Target-URI")
                if UrlUtil.is_relevant_url(record_url): pass
                else:
                    logger.debug(f"Skipping irrelevant URL {record_url}")
                    continue

                if record_url in seen_urls:
                    logger.debug(f"Skipping already seen URL {record_url}.")
                    continue

                # filter by media mimetypes
                content_type = record.http_headers.get("Content-Type")
                if content_type: pass
                else: continue

                if any(x in content_type for x in ["video", "image", "audio"]): pass
                else: continue

                # create local file and add media
                ext = mimetypes.guess_extension(content_type)

                warc_fn = f"warc-file-{counter_warc_files}{ext}"

                fn = os.path.join(tmp_dir, warc_fn)

                with open(fn, "wb") as outf:
                    outf.write(record.raw_stream.read())

                fs = os.path.getsize(fn)
                if fs < 13500 and ext == ".jpg": continue
                if fs < 6000 and ext == ".webp": continue
                if fs < 37000 and ext == ".png": continue
                if fs < 12000 and ext == ".avif": continue
                if ext == ".gif": continue
                if ext == ".ico": continue
                if ext == None : continue

                logger.debug(f"Part 1 - Strategy 0 - saving the single relevant full resolution image from wacz")
                logger.debug(f"Part 1 - Added {fn} which is {fs} and extension {ext}")
                m = Media(filename=fn)
                m.set("src", record_url)

                to_enrich.add_media(m, warc_fn)
                counter_warc_files += 1
                seen_urls.add(record_url)
        logger.info(
            f"Facebook WACZ extract_media/extract_screenshot finished, found {counter_warc_files + counter_screenshots} relevant media file(s)"
        )



    # only used by FB - Part 2
    def save_images_to_enrich_object_from_url_using_browsertrix(self, url_build, to_enrich: Metadata, current_fb_id):
            logger.debug(f' Inside Part 2')
            # call browsertrix and get a warc file using a logged in facebook profile
            # this will get full resolution image which we can then save as a jpg

            with open('url.txt', 'w') as file:
                file.write(url_build)

            collection = random_str(8)

            linux_tmp_dir = os.path.expanduser('~/aatmp')

            # DM 31st Oct 24 take out
            # hard_code_directory_for_wsl2 ='/mnt/c/dev/v6-auto-archiver' 
            # browsertrix_home = ""
            # tmp_dir = ArchivingContext.get_tmp_dir()
            # try:
            #     # DM get strange AttributeError if include self.browsertrix_home - taken out for now 
            #     # browsertrix_home = self.browsertrix_home or os.path.abspath(ArchivingContext.get_tmp_dir())
            #     # browsertrix_home = os.path.abspath(ArchivingContext.get_tmp_dir())
            #     browsertrix_home = os.path.abspath(tmp_dir)
            # except FileNotFoundError: 
            #     logger.debug(f'Dev found in function 2')
            #     # tmp_dir = ArchivingContext.get_tmp_dir()
            #     foo = tmp_dir[1:]
            #     browsertrix_home = f'{hard_code_directory_for_wsl2}{foo}'

            browsertrix_home = linux_tmp_dir

            docker_commands = ["docker", "run", "--rm", "-v", f"{browsertrix_home}:/crawls/", "webrecorder/browsertrix-crawler"]
            cmd = docker_commands + [
                "crawl",
                "--url", url_build,
                "--scopeType", "page",
                "--generateWACZ",
                "--text",
                "--screenshot", "fullPage",
                "--collection", collection,
                "--behaviors", "autoscroll,autoplay,autofetch,siteSpecific",
                "--behaviorTimeout", str(self.timeout),
                "--timeout", str(self.timeout),
                "--combineWarc"
            ]

            if self.profile:
                profile_fn = os.path.join(browsertrix_home, "profile.tar.gz")
                logger.debug(f"copying {self.profile} to {profile_fn}")
                shutil.copyfile(self.profile, profile_fn)
                cmd.extend(["--profile", os.path.join("/crawls", "profile.tar.gz")])

            try:
                logger.info(f"Running browsertrix-crawler: {' '.join(cmd)}")
                subprocess.run(cmd, check=True)
            except Exception as e:
                logger.error(f"WACZ generation failed: {e}")
                return False

            if os.getenv('RUNNING_IN_DOCKER'):
                filename = os.path.join("collections", collection, f"{collection}.wacz")
            else:
                filename = os.path.join(browsertrix_home, "collections", collection, f"{collection}_0.warc.gz")

            if not os.path.exists(filename):
                logger.warning(f"Unable to locate and upload WACZ  {filename=}")
                return False

            warc_filename = filename
            counter = 100
            seen_urls = set()
            # next_fb_id = 0
            list_of_next_fb_ids = []
            with open(warc_filename, 'rb') as warc_stream:
                for record in ArchiveIterator(warc_stream):

                    # 1.Get next fb_id logic
                    if record.rec_type == 'request': 
                        uri = record.rec_headers.get_header('WARC-Target-URI')
                        if "bulk-route-definitions/" in uri:
                            content = record.content_stream().read()
                            foo = str(content)

                            # Strategy 1 test
                            # photo%2F%3Ffbid%3D1646726009098072%26set%3Dpcb.1646726145764725%26
                            # fbid = 1646726009098072
                            # set = pcb.1646726145764725
                            photo_string_start_pos = foo.find(f'photo%2F%3Ffbid%3D',0)
                            # photo_string_start_pos = foo.find(f'%2Fphotos%2Fpcb.',0)
  

                            if (photo_string_start_pos > 0):
                                fbid_start_pos = photo_string_start_pos + 18

                                middle_26_start_pos = foo.find(f'%26', fbid_start_pos)
    
                                # only need this!
                                next_fb_id_foo = foo[fbid_start_pos:middle_26_start_pos]

                                # check haven't found current page fb_id
                                if next_fb_id_foo == current_fb_id:
                                    logger.debug("found current fb_id so ignoring")
                                else:
                                    # next_fb_id = next_fb_id_foo
                                    list_of_next_fb_ids.append(next_fb_id_foo)
                                    # logger.debug(f'Part 2 - appending fb_id {next_fb_id}')

                            # else:
                                # logger.debug('photo string not found in bulk-route-definitions - this is normal. 1 out of 3 have seen work')
                                

                        continue # to next record

                    # DM 12th June 25
                    # am getting weird links coming here which are not part of a carousel
                    # so if is this true, then there is no next_fb_id, so go to next record
                    if len(list_of_next_fb_ids) == 0: 
                        # logger.debug(f"Part 2 - probably a spurious record as couldn't find a next fb_id so not the carousel we want")
                        continue

                    # the response record should have a full res image   
                    if record.rec_type == 'response': pass
                    else: continue # to next record

                    record_url = record.rec_headers.get_header('WARC-Target-URI')
                    
                    content_type = record.http_headers.get("Content-Type")
                    if not content_type: continue
                    if not any(x in content_type for x in ["video", "image", "audio"]): continue

                    # DM - ignore this specialised content type for facebook
                    if content_type == "image/x.fb.keyframes": continue

                    # create local file with correct extension
                    ext = mimetypes.guess_extension(content_type)
                    if ext == None and content_type == "image/x-icon":
                        logger.debug(f"Part 2 - content_type {content_type} has not guessed correct extension. Ignoring.")
                        continue

                    if ext == None:
                        logger.warning(f"Part 2 - content_type {content_type}. Not seen before. Investigate.")
                        continue
                    
                    warc_fn = f"warc-file-{collection}-{counter}{ext}"
                    fn = os.path.join(linux_tmp_dir, warc_fn)

                    with open(fn, "wb") as outf: outf.write(record.raw_stream.read())

                    fs = os.path.getsize(fn)

                    should_add_media = True
                    if fs < 13500 and ext == ".jpg": should_add_media = False
                    if fs < 6000 and ext == ".webp": should_add_media = False
                    if fs < 37000 and ext == ".png": should_add_media = False
                    if fs < 12000 and ext == ".avif": should_add_media = False
                    if ext == ".gif": should_add_media = False
                    if ext == ".ico": should_add_media = False
                    if ext == None : should_add_media = False

                    # add media
                    # there will be duplicates but deduplication is handled in the file upload code 
                    if should_add_media:
                        m = Media(filename=fn)
                        m.set("src", record_url)
                        m.set("src_alternative", record_url)
                        to_enrich.add_media(m, warc_fn)
                        logger.debug(f"Part 2 - Added {fn} which is {fs} bytes and extension {ext}")
                        counter += 1 # starts at 100 and makes filename unique  
                        seen_urls.add(record_url)
                    else:
                        # delete from the tmp_dir so I can see what is there for debugging
                        os.remove(fn)
                    
                    # logger.debug('Part 2 - On to next record')

            # is normally a list of 2 id's for a carousel
            return list_of_next_fb_ids


    # Extract media for non FB link
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
        counter_warc_files = 0
        counter_screenshots = 0
        seen_urls = set()

        with open(warc_filename, "rb") as warc_stream:
            for record in ArchiveIterator(warc_stream):
                # only include fetched resources
                if (
                    record.rec_type == "resource" and record.content_type == "image/png" and self.extract_screenshot
                ):  # screenshots
                    fn = os.path.join(tmp_dir, f"browsertrix-screenshot-{counter_screenshots}.png")
                    with open(fn, "wb") as outf:
                        outf.write(record.raw_stream.read())
                    m = Media(filename=fn)
                    to_enrich.add_media(m, f"browsertrix-screenshot-{counter_screenshots}")
                    counter_screenshots += 1
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
                warc_fn = f"warc-file-{counter_warc_files}{ext}"
                fn = os.path.join(tmp_dir, warc_fn)

                record_url_best_qual = UrlUtil.twitter_best_quality_url(record_url)
                with open(fn, "wb") as outf:
                    outf.write(record.raw_stream.read())

                # DM 28th May 25 - special cases Instagram
                if 'instagram' in record_url:
                    # https://static.cdninstagram.com/images/instagram/xig_legacy_spritesheets/sprite_core.png?__makehaste_cache_breaker=VftLCxPPZoi
                    # https://www.instagram.com/images/instagram/xig_legacy_spritesheets/sprite_compassion_2x.png?__makehaste_cache_breaker=qw4qS1SUQa2
                    if '__makehaste_cache_breaker' in record_url:
                        continue
                    # phone image and icons
                    if 'https://www.instagram.com/rsrc.php/v4/' in record_url:
                        continue

                # DM 22nd May 25 - only want larger more important images 
                fs = os.path.getsize(fn)
                if fs < 13500 and ext == ".jpg": continue
                if fs < 6000 and ext == ".webp": continue
                # png's I see them mostly as graphics or artwork.
                # screenshots are pngs from browsertrix
                if fs < 37000 and ext == ".png": continue
                # youtube
                if fs < 12000 and ext == ".avif": continue
                if ext == ".gif": continue
                if ext == ".ico": continue
                if ext == None : continue

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
                counter_warc_files += 1
                seen_urls.add(record_url)
        logger.info(
            f"WACZ extract_media/extract_screenshot finished, found {counter_warc_files + counter_screenshots} relevant media file(s)"
        )
