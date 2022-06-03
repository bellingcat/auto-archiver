from loguru import logger
from .base_storage import Storage
from dataclasses import dataclass

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

import time


@dataclass
class GDConfig:
    root_folder_id: str
    default_upload_folder_name: str = "default"


class GDStorage(Storage):
    def __init__(self, config: GDConfig):
        self.default_upload_folder_name = config.default_upload_folder_name
        self.root_folder_id = config.root_folder_id
        creds = service_account.Credentials.from_service_account_file('service_account.json', scopes=['https://www.googleapis.com/auth/drive'])
        self.service = build('drive', 'v3', credentials=creds)

    def get_cdn_url(self, key):
        """
        only support files saved in a folder for GD
        S3 supports folder and all stored in the root
        """
        self.subfolder = self._clean_path(self.subfolder, self.default_upload_folder_name, False)
        filename = key
        logger.debug(f'Looking for {self.subfolder} and filename: {filename} on GD')

        folder_id = self._get_id_from_parent_and_name(self.root_folder_id, self.subfolder, 5, 10)

        # check for sub folder in file youtube_dl_abcde/index.html, needed for thumbnails
        # a='youtube_dl_abcde', b='index.html'
        a, _, b = filename.partition('/')
        if b != '':
            logger.debug(f'get_cdn_url: Found a subfolder so need to split on: {a=} and {b=}')
            folder_id = self._get_id_from_parent_and_name(folder_id, a, use_mime_type=True)
            filename = b

        # get id of file inside folder (or sub folder)
        file_id = self._get_id_from_parent_and_name(folder_id, filename)
        return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

    def exists(self, _key):
        # TODO: How to check for google drive, as it accepts different names?
        return False

    def uploadf(self, file, key, **_kwargs):
        """
        1. check if subfolder exists or create it
        2. check if key contains sub-subfolder, check if exists or create it
        3. upload file to root_id/subfolder[/sub-subfolder]/filename
        """
        self.subfolder = self._clean_path(self.subfolder, GDStorage.DEFAULT_UPLOAD_FOLDER_NAME, False)
        filename = key

        # get id of subfolder or create if it does not exist
        folder_id_to_upload_to = self._get_id_from_parent_and_name(self.root_folder_id, self.subfolder, use_mime_type=True, raise_on_missing=False)
        if folder_id_to_upload_to is None:
            folder_id_to_upload_to = self._mkdir(self.subfolder, self.root_folder_id)

        # check for sub folder in file youtube_dl_abcde/index.html, needed for thumbnails
        # a='youtube_dl_abcde', b='index.html'
        a, _, b = filename.partition('/')
        if b != '':
            logger.debug(f'uploadf: Found a subfolder so need to split on: {a=} and {b=}')
            # get id of subfolder or create if it does not exist
            sub_folder_id_to_upload_to = self._get_id_from_parent_and_name(folder_id_to_upload_to, a, use_mime_type=True, raise_on_missing=False)
            if sub_folder_id_to_upload_to is None:
                sub_folder_id_to_upload_to = self._mkdir(a, folder_id_to_upload_to)

            filename = b
            folder_id_to_upload_to = sub_folder_id_to_upload_to

        # upload file to gd
        file_metadata = {
            'name': [filename],
            'parents': [folder_id_to_upload_to]
        }
        media = MediaFileUpload(file, resumable=True)
        gd_file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logger.debug(f'uploadf: uploaded file {gd_file["id"]} succesfully in folder={folder_id_to_upload_to}')

    def upload(self, filename: str, key: str, **kwargs):
        # GD only requires the filename not a file reader
        logger.debug(f'[{self.__class__.__name__}] uploading file {filename} with key {key}')
        self.uploadf(filename, key, **kwargs)

    def _get_id_from_parent_and_name(self, parent_id: str, name: str, retries: int = 1, sleep_seconds: int = 10, use_mime_type: bool = False, raise_on_missing: bool = True):
        """
        Retrieves the id of a folder or file from its @name and the @parent_id folder
        Optionally does multiple @retries and sleeps @sleep_seconds between them
        If @use_mime_type will restrict search to "mimeType='application/vnd.google-apps.folder'"
        If @raise_on_missing will throw error when not found, or returns None
        Returns the id of the file or folder from its name as a string
        """
        debug_header: str = f"[searching {name=} in {parent_id=}]"
        query_string = f"'{parent_id}' in parents and name = '{name}' "
        if use_mime_type:
            query_string += f" and mimeType='application/vnd.google-apps.folder' "

        for attempt in range(retries):
            results = self.service.files().list(
                q=query_string,
                spaces='drive',  # ie not appDataFolder or photos
                fields='files(id, name)'
            ).execute()
            items = results.get('files', [])

            if len(items) > 0:
                logger.debug(f"{debug_header} found {len(items)} matches, returning last of {','.join([i['id'] for i in items])}")
                return items[-1]['id']
            else:
                logger.debug(f'{debug_header} not found, attempt {attempt+1}/{retries}. sleeping for {sleep_seconds} second(s)')
                if attempt < retries - 1: time.sleep(sleep_seconds)

        if raise_on_missing:
            raise ValueError(f'{debug_header} not found after {retries} attempt(s)')
        return None

    def _mkdir(self, name: str, parent_id: str):
        """
        Creates a new GDrive folder @name inside folder @parent_id
        Returns id of the created folder
        """
        logger.debug(f'[_mkdir] Creating new folder with {name=} inside {parent_id=}')
        file_metadata = {
            'name': [name],
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        gd_folder = self.service.files().create(body=file_metadata, fields='id').execute()
        return gd_folder.get('id')
