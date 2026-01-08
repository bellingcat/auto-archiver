import shutil
import sys
import datetime
import os
import importlib
import subprocess
import traceback
import zipfile

from typing import Generator, Type
from urllib.request import urlretrieve

import yt_dlp
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import MaxDownloadsReached
import pysubs2

from auto_archiver.utils.custom_logger import logger

from auto_archiver.core.extractor import Extractor
from auto_archiver.core import Metadata, Media
from auto_archiver.utils import get_datetime_from_str
from auto_archiver.utils.misc import ydl_entry_to_filename
from .dropin import GenericDropin


class SkipYtdlp(Exception):
    pass


class GenericExtractor(Extractor):
    _dropins = {}

    def setup(self):
        self.check_for_extractor_updates()
        self.setup_po_tokens()
        # TODO: figure out why the following is not properly recognised by yt-dlp:
        # if "generic" not in self.extractor_args:
        #     self.extractor_args["generic"] = "impersonate"

    def check_for_extractor_updates(self):
        """Checks whether yt-dlp or its plugins need updating and triggers a restart if so."""
        if self.ytdlp_update_interval < 0:
            return

        update_file = os.path.join("secrets" if os.path.exists("secrets") else "", ".ytdlp-update")
        next_check = None
        if os.path.exists(update_file):
            with open(update_file, "r") as f:
                next_check = datetime.datetime.fromisoformat(f.read())

        if next_check and next_check > datetime.datetime.now():
            return

        yt_dlp_updated = self.update_package("yt-dlp")
        bgutil_updated = self.update_package("bgutil-ytdlp-pot-provider")

        # Write the new timestamp
        with open(update_file, "w") as f:
            next_check = datetime.datetime.now() + datetime.timedelta(days=self.ytdlp_update_interval)
            f.write(next_check.isoformat())

        if yt_dlp_updated or bgutil_updated:
            if os.environ.get("AUTO_ARCHIVER_ALLOW_RESTART", "1") != "1":
                logger.warning("yt-dlp or plugin was updated — please restart auto-archiver manually")
            else:
                logger.warning("yt-dlp or plugin was updated — restarting auto-archiver\n ======= RESTARTING ======= ")
                os.execv(sys.executable, [sys.executable] + sys.argv)

    def update_package(self, package_name: str) -> bool:
        logger.info(f"Checking and updating {package_name}...")
        from importlib.metadata import version as get_version

        old_version = get_version(package_name)
        try:
            result = subprocess.run(["pip", "install", "--upgrade", package_name], check=True, capture_output=True)
            if f"Successfully installed {package_name}" in result.stdout.decode():
                new_version = importlib.metadata.version(package_name)
                logger.info(f"{package_name} updated from {old_version} to {new_version}")
                return True
            logger.info(f"{package_name} already up to date")
        except Exception as e:
            logger.error(f"Failed to update {package_name}: {e}")
        return False

    def setup_po_tokens(self) -> None:
        """Setup Proof of Origin Token method conditionally.
        Uses provider: https://github.com/Brainicism/bgutil-ytdlp-pot-provider.
        """
        in_docker = os.environ.get("RUNNING_IN_DOCKER")
        if self.bguils_po_token_method == "disabled":
            # This allows disabling of the PO Token generation script in the Docker implementation.
            logger.warning("Proof of Origin Token generation is disabled.")
            return

        if self.bguils_po_token_method == "auto" and not in_docker:
            logger.info(
                "Proof of Origin Token method not explicitly set. "
                "If you're running an external HTTP server separately, you can safely ignore this message. "
                "To reduce the likelihood of bot detection, enable one of the methods described in the documentation: "
                "https://auto-archiver.readthedocs.io/en/settings_page/installation/authentication.html#proof-of-origin-tokens"
            )
            return

        # Either running in Docker, or "script" method is set beyond this point
        self.setup_token_generation_script()

    def setup_token_generation_script(self) -> None:
        """This function sets up the Proof of Origin Token generation script method for
        bgutil-ytdlp-pot-provider if enabled or in Docker."""
        missing_tools = [tool for tool in ("node", "yarn", "npx") if shutil.which(tool) is None]
        if missing_tools:
            logger.error(
                f"Cannot set up PO Token script; missing required tools: {', '.join(missing_tools)}. "
                "Install these tools or run bgutils via Docker. "
                "See: https://github.com/Brainicism/bgutil-ytdlp-pot-provider"
            )
            return
        try:
            from importlib.metadata import version as get_version

            plugin_version = get_version("bgutil-ytdlp-pot-provider")
            base_dir = os.path.expanduser("~/bgutil-ytdlp-pot-provider")
            server_dir = os.path.join(base_dir, "server")
            version_file = os.path.join(server_dir, ".VERSION")
            transpiled_script = os.path.join(server_dir, "build", "generate_once.js")

            # Skip setup if version is correct and transpiled script exists
            if os.path.isfile(transpiled_script) and os.path.isfile(version_file):
                with open(version_file) as vf:
                    if vf.read().strip() == plugin_version:
                        logger.info("PO Token script already set up and up to date.")
            else:
                # Remove an outdated directory and pull a new version
                if os.path.exists(base_dir):
                    shutil.rmtree(base_dir)
                os.makedirs(base_dir, exist_ok=True)

                zip_url = (
                    f"https://github.com/Brainicism/bgutil-ytdlp-pot-provider/archive/refs/tags/{plugin_version}.zip"
                )
                zip_path = os.path.join(base_dir, f"{plugin_version}.zip")
                logger.info(f"Downloading bgutils release zip for version {plugin_version}...")
                urlretrieve(zip_url, zip_path)
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(base_dir)
                os.remove(zip_path)

                extracted_root = os.path.join(base_dir, f"bgutil-ytdlp-pot-provider-{plugin_version}")
                shutil.move(os.path.join(extracted_root, "server"), server_dir)
                shutil.rmtree(extracted_root)
                logger.info("Installing dependencies and transpiling PoT Generator script...")
                subprocess.run(["yarn", "install", "--frozen-lockfile"], cwd=server_dir, check=True)
                subprocess.run(["npx", "tsc"], cwd=server_dir, check=True)

                with open(version_file, "w") as vf:
                    vf.write(plugin_version)

            script_path = os.path.join(server_dir, "build", "generate_once.js")
            if not os.path.exists(script_path):
                logger.error("generate_once.js not found after transpilation.")
                return

            self.extractor_args.setdefault("youtubepot-bgutilscript", {})["script_path"] = script_path
            logger.info(f"PO Token script configured at: {script_path}")

        except Exception as e:
            logger.error(f"Failed to set up PO Token script: {e}")

    def suitable_extractors(self, url: str) -> Generator[str, None, None]:
        """
        Returns a list of valid extractors for the given URL"""
        for info_extractor in yt_dlp.YoutubeDL()._ies.values():
            if not info_extractor.working():
                continue

            # check if there's a dropin and see if that declares whether it's suitable
            dropin: GenericDropin = self.dropin_for_name(info_extractor.ie_key())
            if dropin and dropin.suitable(url, info_extractor):
                yield info_extractor
            elif info_extractor.suitable(url):
                yield info_extractor

    def suitable(self, url: str) -> bool:
        """
        Checks for valid URLs out of all ytdlp extractors.
        Returns False for the GenericIE, which as labelled by yt-dlp: 'Generic downloader that works on some sites'
        """
        return any(self.suitable_extractors(url))

    def download_additional_media(
        self, video_data: dict, info_extractor: InfoExtractor, metadata: Metadata
    ) -> Metadata:
        """
        Downloads additional media like images, comments, subtitles, etc.

        Creates a 'media' object and attaches it to the metadata object.
        """

        # Just get the main thumbnail. More thumbnails are available in
        # video_data['thumbnails'] should they be required
        thumbnail_url = video_data.get("thumbnail")
        if thumbnail_url:
            try:
                cover_image_path = self.download_from_url(thumbnail_url)
                media = Media(cover_image_path)
                metadata.add_media(media, id="cover")
            except Exception as e:
                logger.error(f"Could not download cover image {thumbnail_url}: {e}")

        dropin = self.dropin_for_name(info_extractor.ie_key())
        if dropin:
            try:
                metadata = dropin.download_additional_media(video_data, info_extractor, metadata)
            except AttributeError:
                pass

        return metadata

    def keys_to_clean(self, info_extractor: InfoExtractor, video_data: dict) -> dict:
        """
        Clean up the ytdlp generic video data to make it more readable and remove unnecessary keys that ytdlp adds
        """

        base_keys = [
            "formats",
            "thumbnail",
            "display_id",
            "epoch",
            "requested_downloads",
            "duration_string",
            "thumbnails",
            "http_headers",
            "webpage_url_basename",
            "webpage_url_domain",
            "extractor",
            "extractor_key",
            "playlist",
            "playlist_index",
            "duration_string",
            "protocol",
            "requested_subtitles",
            "format_id",
            "acodec",
            "vcodec",
            "ext",
            "epoch",
            "_has_drm",
            "filesize",
            "audio_ext",
            "video_ext",
            "vbr",
            "abr",
            "resolution",
            "dynamic_range",
            "aspect_ratio",
            "cookies",
            "format",
            "quality",
            "preference",
            "artists",
            "channel_id",
            "subtitles",
            "tbr",
            "url",
            "original_url",
            "automatic_captions",
            "playable_in_embed",
            "live_status",
            "_format_sort_fields",
            "chapters",
            "requested_formats",
            "format_note",
            "audio_channels",
            "asr",
            "fps",
            "was_live",
            "is_live",
            "heatmap",
            "age_limit",
            "stretched_ratio",
        ]

        dropin = self.dropin_for_name(info_extractor.ie_key())
        if dropin:
            try:
                base_keys += dropin.keys_to_clean(video_data, info_extractor)
            except AttributeError:
                pass

        return base_keys

    def add_metadata(self, video_data: dict, info_extractor: InfoExtractor, url: str, result: Metadata) -> Metadata:
        """
        Creates a Metadata object from the given video_data
        """

        # first add the media
        result = self.download_additional_media(video_data, info_extractor, result)

        # keep both 'title' and 'fulltitle', but prefer 'title', falling back to 'fulltitle' if it doesn't exist
        if not result.get_title():
            result.set_title(video_data.pop("title", video_data.pop("fulltitle", "")))

        if not result.get("url"):
            result.set_url(url)

        if "description" in video_data and not result.get("content"):
            result.set_content(video_data.pop("description"))
        # extract comments if enabled
        if self.comments and video_data.get("comments", None) is not None:
            result.set(
                "comments",
                [
                    {
                        "text": c["text"],
                        "author": c["author"],
                        "timestamp": datetime.datetime.fromtimestamp(c.get("timestamp"), tz=datetime.timezone.utc),
                    }
                    for c in video_data.get("comments", [])
                ],
            )

        # then add the common metadata
        timestamp = video_data.pop("timestamp", None)
        if timestamp and not result.get("timestamp"):
            timestamp = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).isoformat()
            result.set_timestamp(timestamp)

        upload_date = video_data.pop("upload_date", None)
        if upload_date and not result.get("upload_date"):
            upload_date = get_datetime_from_str(upload_date, "%Y%m%d").replace(tzinfo=datetime.timezone.utc)
            result.set("upload_date", upload_date)

        # then clean away any keys we don't want
        for clean_key in self.keys_to_clean(info_extractor, video_data):
            video_data.pop(clean_key, None)

        # then add the rest of the video data
        for k, v in video_data.items():
            if v:
                result.set(k, v)

        return result

    def get_metadata_for_post(self, info_extractor: Type[InfoExtractor], url: str, ydl: yt_dlp.YoutubeDL) -> Metadata:
        """
        Calls into the ytdlp InfoExtract subclass to use the private _extract_post method to get the post metadata.
        """

        ie_instance = info_extractor(downloader=ydl)
        dropin = self.dropin_for_name(info_extractor.ie_key())

        if not dropin:
            # TODO: add a proper link to 'how to create your own dropin'
            logger.debug(f"""Could not find valid dropin for {info_extractor.ie_key()}.
                     Why not try creating your own, and make sure it has a valid function called 'create_metadata'. Learn more: https://auto-archiver.readthedocs.io/en/latest/user_guidelines.html#""")
            return False

        post_data = dropin.extract_post(url, ie_instance)
        result = dropin.create_metadata(post_data, ie_instance, self, url)
        return self.add_metadata(post_data, info_extractor, url, result)

    def get_metadata_for_video(
        self, data: dict, info_extractor: Type[InfoExtractor], url: str, ydl: yt_dlp.YoutubeDL
    ) -> Metadata:
        # this time download
        ydl.params["getcomments"] = self.comments
        # TODO: for playlist or long lists of videos, how to download one at a time so they can be stored before the next one is downloaded?
        try:
            data = ydl.extract_info(url, ie_key=info_extractor.ie_key(), download=True)
        except MaxDownloadsReached:  # proceed as normal once MaxDownloadsReached is raised
            pass

        if "entries" in data:
            entries = data.get("entries", [])
            if not len(entries):
                logger.info("GenericExtractor could not find any video")
                return False
        else:
            entries = [data]
        result = Metadata()

        for entry in entries:
            try:
                filename = ydl_entry_to_filename(ydl, entry)

                if not filename:
                    # file was not downloaded or could not be retrieved, example: sensitive videos on YT without using cookies.
                    continue

                logger.debug(f"Using filename {filename} for entry {entry.get('id', 'unknown')}")

                new_media = Media(filename)
                for x in ["duration", "original_url", "fulltitle", "description", "upload_date"]:
                    if x in entry:
                        new_media.set(x, entry[x])

                # read text from subtitles if enabled
                if self.subtitles:
                    for lang, val in (data.get("requested_subtitles") or {}).items():
                        try:
                            subs = pysubs2.load(val.get("filepath"), encoding="utf-8")
                            text = " ".join([line.text for line in subs])
                            new_media.set(f"subtitles_{lang}", text)
                        except Exception as e:
                            logger.error(f"Error loading subtitle file {val.get('filepath')}: {e}")
                result.add_media(new_media)
            except Exception as e:
                logger.error(f"Error processing entry {str(entry)[:256]}: {e} {traceback.format_exc()}")
        if not len(result.media):
            logger.info(f"No media found for entry {str(entry)[:256]}, skipping.")
            return False

        return self.add_metadata(data, info_extractor, url, result)

    def dropin_for_name(self, dropin_name: str, additional_paths=[], package=__package__) -> GenericDropin:
        dropin_name = dropin_name.lower()

        if dropin_name == "generic":
            # no need for a dropin for the generic extractor (?)
            return None

        dropin_class_name = dropin_name.title()

        def _load_dropin(dropin):
            dropin_class = getattr(dropin, dropin_class_name)()
            dropin.extractor = self
            return self._dropins.setdefault(dropin_name, dropin_class)

        try:
            return self._dropins[dropin_name]
        except KeyError:
            pass

        # TODO: user should be able to pass --dropins="/some/folder,/other/folder" as a cmd line option
        # which would allow the user to override the default dropins/add their own
        paths = [] + additional_paths
        for path in paths:
            dropin_path = os.path.join(path, f"{dropin_name}.py")
            dropin_spec = importlib.util.spec_from_file_location(dropin_name, dropin_path)
            if not dropin_spec:
                continue
            try:
                dropin = importlib.util.module_from_spec(dropin_spec)
                dropin_spec.loader.exec_module(dropin)
                return _load_dropin(dropin)
            except (FileNotFoundError, ModuleNotFoundError):
                pass

        # fallback to loading the dropins within auto-archiver
        try:
            return _load_dropin(importlib.import_module(f".{dropin_name}", package=package))
        except ModuleNotFoundError:
            pass

        return None

    def download_for_extractor(self, info_extractor: InfoExtractor, url: str, ydl: yt_dlp.YoutubeDL) -> Metadata:
        """
        Tries to download the given url using the specified extractor

        It first tries to use ytdlp directly to download the video. If the post is not a video, it will then try to
        use the extractor's _extract_post method to get the post metadata if possible.
        """
        # when getting info without download, we also don't need the comments
        ydl.params["getcomments"] = False
        result = False

        dropin_submodule = self.dropin_for_name(info_extractor.ie_key())

        def _helper_for_successful_extract_info(data, info_extractor, url, ydl):
            if data.get("is_live", False) and not self.livestreams:
                logger.warning("Livestream detected, skipping due to 'livestreams' configuration setting")
                return False
            # it's a valid video, that the youtubdedl can download out of the box
            return self.get_metadata_for_video(data, info_extractor, url, ydl)

        try:
            if dropin_submodule and dropin_submodule.skip_ytdlp_download(url, info_extractor):
                logger.debug(f"Skipping using ytdlp to download files for {info_extractor.ie_key()}")
                raise SkipYtdlp()

            # don't download since it can be a live stream
            data = ydl.extract_info(url, ie_key=info_extractor.ie_key(), download=False)

            result = _helper_for_successful_extract_info(data, info_extractor, url, ydl)

        except MaxDownloadsReached:
            # yt-dlp raises an error when the max downloads limit is reached, and it shouldn't for our purposes, so we consider that a success
            result = _helper_for_successful_extract_info(data, info_extractor, url, ydl)

        except Exception as e:
            if info_extractor.IE_NAME == "generic":
                # don't clutter the logs with issues about the 'generic' extractor not having a dropin
                return False

            if not isinstance(e, SkipYtdlp):
                logger.debug(
                    f'Issue using "{info_extractor.IE_NAME}" extractor to download video (error: {repr(e)}), attempting to use dropin to get post data instead'
                )

            try:
                result = self.get_metadata_for_post(info_extractor, url, ydl)
            except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError) as post_e:
                if "NSFW tweet requires authentication." in str(post_e):
                    logger.warning(str(post_e))
                    return False
                logger.error("Error downloading metadata for post: {error}", error=str(post_e))
                return False
            except Exception as generic_e:
                logger.debug(
                    'Attempt to extract using ytdlp extractor "{name}" failed:  \n  {error}',
                    name=info_extractor.IE_NAME,
                    error=str(generic_e),
                    exc_info=True,
                )
                return False

        if result and not result.is_success():
            extractor_name = "yt-dlp"
            if info_extractor:
                extractor_name += f"_{info_extractor.ie_key()}"

            if self.end_means_success:
                result.success(extractor_name)
            else:
                result.status = extractor_name

        return result

    def download(self, item: Metadata, skip_proxy: bool = False) -> Metadata:
        url = item.get_url()

        # TODO: this is a temporary hack until this issue is closed: https://github.com/yt-dlp/yt-dlp/issues/11025
        if url.startswith("https://ya.ru"):
            url = url.replace("https://ya.ru", "https://yandex.ru")
            item.set("replaced_url", url)

        # proxy_on_failure_only logic
        if self.proxy and self.proxy_on_failure_only and not skip_proxy:
            # when proxy_on_failure_only is True, we first try to download without a proxy and only continue with execution if that fails
            try:
                if without_proxy := self.download(item, skip_proxy=True):
                    logger.info("Downloaded successfully without proxy.")
                    return without_proxy
            except Exception:
                logger.debug("Download without proxy failed, trying with proxy...")

        ydl_options = [
            "-o",
            os.path.join(self.tmp_dir, "%(id)s.%(ext)s"),
            "--quiet",
            "--no-playlist" if not self.allow_playlist else "--yes-playlist",
            "--write-subs" if self.subtitles else "--no-write-subs",
            "--write-auto-subs" if self.subtitles else "--no-write-auto-subs",
            "--live-from-start" if self.live_from_start else "--no-live-from-start",
            "--postprocessor-args",
            "ffmpeg:-bitexact",  # ensure bitexact output to avoid mismatching hashes for same video
        ]

        # proxy handling
        if self.proxy and not skip_proxy:
            ydl_options.extend(["--proxy", self.proxy])

        # max_downloads handling
        if self.max_downloads != "inf":
            ydl_options.extend(["--max-downloads", str(self.max_downloads)])
            ydl_options.extend(["--playlist-end", str(self.max_downloads)])

        # set up auth
        auth = self.auth_for_site(url, extract_cookies=False)
        # order of importance: username/password -> api_key -> cookie -> cookies_from_browser -> cookies_file
        if auth:
            if "username" in auth and "password" in auth:
                logger.debug("Using provided auth username and password")
                ydl_options.extend(("--username", auth["username"]))
                ydl_options.extend(("--password", auth["password"]))
            elif "cookie" in auth:
                logger.debug("Using provided auth cookie")
                yt_dlp.utils.std_headers["cookie"] = auth["cookie"]
            elif "cookies_from_browser" in auth:
                logger.debug(f"Using extracted cookies from browser {auth['cookies_from_browser']}")
                ydl_options.extend(("--cookies-from-browser", auth["cookies_from_browser"]))
            elif "cookies_file" in auth:
                logger.debug(f"Using cookies from file {auth['cookies_file']}")
                ydl_options.extend(("--cookies", auth["cookies_file"]))

        # Applying user-defined extractor_args
        if self.extractor_args:
            for key, args in self.extractor_args.items():
                if isinstance(args, dict):
                    arg_str = ";".join(f"{k}={v}" for k, v in args.items())
                else:
                    arg_str = str(args)
                logger.debug(f"Setting extractor_args: {key}:{arg_str}")
                ydl_options.extend(["--extractor-args", f"{key}:{arg_str}"])

        if self.ytdlp_args:
            logger.debug(f"Adding additional ytdlp arguments: {self.ytdlp_args}")
            ydl_options += self.ytdlp_args.split(" ")

        *_, validated_options = yt_dlp.parse_options(ydl_options)
        ydl = yt_dlp.YoutubeDL(
            validated_options
        )  # allsubtitles and subtitleslangs not working as expected, so default lang is always "en"

        result: Metadata = None
        for info_extractor in self.suitable_extractors(url):
            local_result: Metadata = self.download_for_extractor(info_extractor, url, ydl)
            if local_result:
                result = result.merge(local_result) if result else local_result
        return result if result else False
