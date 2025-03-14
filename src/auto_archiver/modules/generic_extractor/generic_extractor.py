import datetime
import os
import importlib
import subprocess

from typing import Generator, Type

import yt_dlp
from yt_dlp.extractor.common import InfoExtractor
import pysubs2

from loguru import logger

from auto_archiver.core.extractor import Extractor
from auto_archiver.core import Metadata, Media


class SkipYtdlp(Exception):
    pass


class GenericExtractor(Extractor):
    _dropins = {}

    def setup(self):
        # check for file .ytdlp-update in the secrets folder
        if self.ytdlp_update_interval < 0:
            return

        use_secrets = os.path.exists("secrets")
        path = os.path.join("secrets" if use_secrets else "", ".ytdlp-update")
        next_update_check = None
        if os.path.exists(path):
            with open(path, "r") as f:
                next_update_check = datetime.datetime.fromisoformat(f.read())

        if not next_update_check or next_update_check < datetime.datetime.now():
            self.update_ytdlp()

            next_update_check = datetime.datetime.now() + datetime.timedelta(days=self.ytdlp_update_interval)
            with open(path, "w") as f:
                f.write(next_update_check.isoformat())

    def update_ytdlp(self):
        logger.info("Checking and updating yt-dlp...")
        logger.info(
            f"Tip: change the 'ytdlp_update_interval' setting to control how often yt-dlp is updated. Set to -1 to disable or 0 to enable on every run. Current setting: {self.ytdlp_update_interval}"
        )
        from importlib.metadata import version as get_version

        old_version = get_version("yt-dlp")
        try:
            # try and update with pip (this works inside poetry environment and in a normal virtualenv)
            result = subprocess.run(["pip", "install", "--upgrade", "yt-dlp"], check=True, capture_output=True)

            if "Successfully installed yt-dlp" in result.stdout.decode():
                new_version = importlib.metadata.version("yt-dlp")
                logger.info(f"yt-dlp successfully (from {old_version} to {new_version})")
                importlib.reload(yt_dlp)
            else:
                logger.info("yt-dlp already up to date")

        except Exception as e:
            logger.error(f"Error updating yt-dlp: {e}")

    def suitable_extractors(self, url: str) -> Generator[str, None, None]:
        """
        Returns a list of valid extractors for the given URL"""
        for info_extractor in yt_dlp.YoutubeDL()._ies.values():
            if info_extractor.suitable(url) and info_extractor.working():
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
                logger.error(f"Error downloading cover image {thumbnail_url}: {e}")

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
        result.set_title(video_data.pop("title", video_data.pop("fulltitle", "")))
        result.set_url(url)
        if "description" in video_data:
            result.set_content(video_data["description"])
        # extract comments if enabled
        if self.comments:
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
        if timestamp := video_data.pop("timestamp", None):
            timestamp = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).isoformat()
            result.set_timestamp(timestamp)
        if upload_date := video_data.pop("upload_date", None):
            upload_date = datetime.datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=datetime.timezone.utc)
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
        return dropin.create_metadata(post_data, ie_instance, self, url)

    def get_metadata_for_video(
        self, data: dict, info_extractor: Type[InfoExtractor], url: str, ydl: yt_dlp.YoutubeDL
    ) -> Metadata:
        # this time download
        ydl.params["getcomments"] = self.comments
        # TODO: for playlist or long lists of videos, how to download one at a time so they can be stored before the next one is downloaded?
        data = ydl.extract_info(url, ie_key=info_extractor.ie_key(), download=True)
        if "entries" in data:
            entries = data.get("entries", [])
            if not len(entries):
                logger.warning("YoutubeDLArchiver could not find any video")
                return False
        else:
            entries = [data]

        result = Metadata()

        for entry in entries:
            try:
                filename = ydl.prepare_filename(entry)
                if not os.path.exists(filename):
                    filename = filename.split(".")[0] + ".mkv"

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
                logger.error(f"Error processing entry {entry}: {e}")

        return self.add_metadata(data, info_extractor, url, result)

    def dropin_for_name(self, dropin_name: str, additional_paths=[], package=__package__) -> Type[InfoExtractor]:
        dropin_name = dropin_name.lower()

        if dropin_name == "generic":
            # no need for a dropin for the generic extractor (?)
            return None

        dropin_class_name = dropin_name.title()

        def _load_dropin(dropin):
            dropin_class = getattr(dropin, dropin_class_name)()
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

        try:
            if dropin_submodule and dropin_submodule.skip_ytdlp_download(info_extractor, url):
                logger.debug(f"Skipping using ytdlp to download files for {info_extractor.ie_key()}")
                raise SkipYtdlp()

            # don't download since it can be a live stream
            data = ydl.extract_info(url, ie_key=info_extractor.ie_key(), download=False)
            if data.get("is_live", False) and not self.livestreams:
                logger.warning("Livestream detected, skipping due to 'livestreams' configuration setting")
                return False
            # it's a valid video, that the youtubdedl can download out of the box
            result = self.get_metadata_for_video(data, info_extractor, url, ydl)

        except Exception as e:
            if info_extractor.IE_NAME == "generic":
                # don't clutter the logs with issues about the 'generic' extractor not having a dropin
                return False

            if not isinstance(e, SkipYtdlp):
                logger.debug(
                    f'Issue using "{info_extractor.IE_NAME}" extractor to download video (error: {repr(e)}), attempting to use extractor to get post data instead'
                )

            try:
                result = self.get_metadata_for_post(info_extractor, url, ydl)
            except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError) as post_e:
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

        if result:
            extractor_name = "yt-dlp"
            if info_extractor:
                extractor_name += f"_{info_extractor.ie_key()}"

            if self.end_means_success:
                result.success(extractor_name)
            else:
                result.status = extractor_name

        return result

    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()

        # TODO: this is a temporary hack until this issue is closed: https://github.com/yt-dlp/yt-dlp/issues/11025
        if url.startswith("https://ya.ru"):
            url = url.replace("https://ya.ru", "https://yandex.ru")
            item.set("replaced_url", url)

        ydl_options = [
            "-o",
            os.path.join(self.tmp_dir, f"%(id)s.%(ext)s"),
            "--quiet",
            "--no-playlist" if not self.allow_playlist else "--yes-playlist",
            "--write-subs" if self.subtitles else "--no-write-subs",
            "--write-auto-subs" if self.subtitles else "--no-write-auto-subs",
            "--live-from-start" if self.live_from_start else "--no-live-from-start",
            "--proxy",
            self.proxy if self.proxy else "",
            f"--max-downloads {self.max_downloads}" if self.max_downloads != "inf" else "",
            f"--playlist-end {self.max_downloads}" if self.max_downloads != "inf" else "",
        ]

        # set up auth
        auth = self.auth_for_site(url, extract_cookies=False)

        # order of importance: username/pasword -> api_key -> cookie -> cookies_from_browser -> cookies_file
        if auth:
            if "username" in auth and "password" in auth:
                logger.debug(f"Using provided auth username and password for {url}")
                ydl_options.extend(("--username", auth["username"]))
                ydl_options.extend(("--password", auth["password"]))
            elif "cookie" in auth:
                logger.debug(f"Using provided auth cookie for {url}")
                yt_dlp.utils.std_headers["cookie"] = auth["cookie"]
            elif "cookies_from_browser" in auth:
                logger.debug(f"Using extracted cookies from browser {auth['cookies_from_browser']} for {url}")
                ydl_options.extend(("--cookies-from-browser", auth["cookies_from_browser"]))
            elif "cookies_file" in auth:
                logger.debug(f"Using cookies from file {auth['cookies_file']} for {url}")
                ydl_options.extend(("--cookies", auth["cookies_file"]))

        if self.ytdlp_args:
            logger.debug("Adding additional ytdlp arguments: {self.ytdlp_args}")
            ydl_options += self.ytdlp_args.split(" ")

        *_, validated_options = yt_dlp.parse_options(ydl_options)
        ydl = yt_dlp.YoutubeDL(
            validated_options
        )  # allsubtitles and subtitleslangs not working as expected, so default lang is always "en"

        for info_extractor in self.suitable_extractors(url):
            result = self.download_for_extractor(info_extractor, url, ydl)
            if result:
                return result

        return False
