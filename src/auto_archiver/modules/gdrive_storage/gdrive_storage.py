import json
import os
import time
from typing import IO

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from auto_archiver.utils.custom_logger import logger

from auto_archiver.core import Media
from auto_archiver.core import Storage


class GDriveStorage(Storage):
    def setup(self) -> None:
        self.scopes = ["https://www.googleapis.com/auth/drive"]
        # Initialize Google Drive service
        self._setup_google_drive_service()

    def _setup_google_drive_service(self):
        """Initialize Google Drive service based on provided credentials."""
        if self.oauth_token:
            logger.debug(f"Using Google Drive OAuth token: {self.oauth_token}")
            self.service = self._initialize_with_oauth_token()
        elif self.service_account:
            logger.debug(f"Using Google Drive service account: {self.service_account}")
            self.service = self._initialize_with_service_account()
        else:
            raise ValueError("Missing credentials: either `oauth_token` or `service_account` must be provided.")

    def _initialize_with_oauth_token(self):
        """Initialize Google Drive service with OAuth token."""
        with open(self.oauth_token, "r") as stream:
            creds_json = json.load(stream)
            creds_json["refresh_token"] = creds_json.get("refresh_token", "")

        creds = Credentials.from_authorized_user_info(creds_json, self.scopes)
        if not creds.valid and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(self.oauth_token, "w") as token_file:
                logger.debug("Saving refreshed OAuth token.")
                token_file.write(creds.to_json())
        elif not creds.valid:
            raise ValueError("Invalid OAuth token. Please regenerate the token.")

        return build("drive", "v3", credentials=creds)

    def _initialize_with_service_account(self):
        """Initialize Google Drive service with service account."""
        creds = service_account.Credentials.from_service_account_file(self.service_account, scopes=self.scopes)
        return build("drive", "v3", credentials=creds)

    def get_cdn_url(self, media: Media) -> str:
        """
        only support files saved in a folder for GD
        S3 supports folder and all stored in the root
        """
        # full_name = os.path.join(self.folder, media.key)
        parent_id, folder_id = self.root_folder_id, None
        path_parts = media.key.split(os.path.sep)
        filename = path_parts[-1]
        logger.info(f"Looking for folders for {path_parts[0:-1]} before getting url for {filename=}")
        for folder in path_parts[0:-1]:
            folder_id = self._get_id_from_parent_and_name(parent_id, folder, use_mime_type=True, raise_on_missing=True)
            parent_id = folder_id
        # get id of file inside folder (or sub folder)
        file_id = self._get_id_from_parent_and_name(folder_id, filename, raise_on_missing=True)
        if not file_id:
            #
            logger.info(f"File {filename} not found in folder {folder_id}")
            return None
        return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

    def upload(self, media: Media, **kwargs) -> bool:
        logger.debug(f"[{self.__class__.__name__}] storing file {media.filename} with key {media.key}")
        """
        1. for each sub-folder in the path check if exists or create
        2. upload file to root_id/other_paths.../filename
        """
        parent_id, upload_to = self.root_folder_id, None
        path_parts = media.key.split(os.path.sep)
        filename = path_parts[-1]
        logger.info(f"Checking folders {path_parts[0:-1]} exist (or creating) before uploading {filename=}")
        for folder in path_parts[0:-1]:
            upload_to = self._get_id_from_parent_and_name(parent_id, folder, use_mime_type=True, raise_on_missing=False)
            if upload_to is None:
                upload_to = self._mkdir(folder, parent_id)
            parent_id = upload_to

        # upload file to gd
        logger.debug(f"Uploading {filename=} to folder id {upload_to}")
        file_metadata = {"name": [filename], "parents": [upload_to]}
        try:
            media = MediaFileUpload(media.filename, resumable=True)
            gd_file = (
                self.service.files()
                .create(supportsAllDrives=True, body=file_metadata, media_body=media, fields="id")
                .execute()
            )
            logger.debug(f"Uploadf: uploaded file {gd_file['id']} successfully in folder={upload_to}")
        except FileNotFoundError as e:
            logger.error(f"GD uploadf: file not found {media.filename=} - {e}")
        except Exception as e:
            logger.error(f"GD uploadf: error uploading {media.filename=} to {upload_to} - {e}")

    # must be implemented even if unused
    def uploadf(self, file: IO[bytes], key: str, **kwargs: dict) -> bool:
        pass

    def _get_id_from_parent_and_name(
        self,
        parent_id: str,
        name: str,
        retries: int = 1,
        sleep_seconds: int = 10,
        use_mime_type: bool = False,
        raise_on_missing: bool = True,
        use_cache=False,
    ):
        """
        Retrieves the id of a folder or file from its @name and the @parent_id folder
        Optionally does multiple @retries and sleeps @sleep_seconds between them
        If @use_mime_type will restrict search to "mimeType='application/vnd.google-apps.folder'"
        If @raise_on_missing will throw error when not found, or returns None
        Will remember previous calls to avoid duplication if @use_cache - might not have all edge cases tested, so use at own risk
        Returns the id of the file or folder from its name as a string
        """
        # cache logic
        if use_cache:
            self.api_cache = getattr(self, "api_cache", {})
            cache_key = f"{parent_id}_{name}_{use_mime_type}"
            if cache_key in self.api_cache:
                logger.debug(f"Cache hit for {cache_key=}")
                return self.api_cache[cache_key]

        # API logic
        debug_header: str = f"[searching {name=} in {parent_id=}]"
        query_string = f"'{parent_id}' in parents and name = '{name}' and trashed = false "
        if use_mime_type:
            query_string += " and mimeType='application/vnd.google-apps.folder' "

        for attempt in range(retries):
            results = (
                self.service.files()
                .list(
                    # both below for Google Shared Drives
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    q=query_string,
                    spaces="drive",  # ie not appDataFolder or photos
                    fields="files(id, name)",
                )
                .execute()
            )
            items = results.get("files", [])

            if len(items) > 0:
                logger.debug(
                    f"{debug_header} found {len(items)} matches, returning last of {','.join([i['id'] for i in items])}"
                )
                _id = items[-1]["id"]
                if use_cache:
                    self.api_cache[cache_key] = _id
                return _id
            else:
                logger.debug(f"{debug_header} not found, attempt {attempt + 1}/{retries}.")
                if attempt < retries - 1:
                    logger.debug(f"Sleeping for {sleep_seconds} second(s)")
                    time.sleep(sleep_seconds)

        if raise_on_missing:
            raise ValueError(f"{debug_header} not found after {retries} attempt(s)")
        return None

    def _mkdir(self, name: str, parent_id: str):
        """
        Creates a new GDrive folder @name inside folder @parent_id
        Returns id of the created folder
        """
        logger.debug(f"Creating new folder with {name=} inside {parent_id=}")
        file_metadata = {"name": [name], "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
        gd_folder = self.service.files().create(supportsAllDrives=True, body=file_metadata, fields="id").execute()
        return gd_folder.get("id")
