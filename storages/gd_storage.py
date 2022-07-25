import os, time

from loguru import logger
from .base_storage import Storage
from dataclasses import dataclass
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account


from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

@dataclass
class GDConfig:
    root_folder_id: str
    oauth_token_filename: str
    service_account: str = "service_account.json"
    folder: str = "default"

class GDStorage(Storage):
    def __init__(self, config: GDConfig):
        self.folder = config.folder
        self.root_folder_id = config.root_folder_id
        
        SCOPES=['https://www.googleapis.com/auth/drive']
        
        token_file = config.oauth_token_filename
        if token_file is not None:
            """
            Tokens are refreshed after 1 hour
            however keep working for 7 days (tbc)
            so as long as the job doesn't last for 7 days
            then this method of refreshing only once per run will work
            see this link for details on the token
            https://davemateer.com/2022/04/28/google-drive-with-python#tokens
            """
            logger.debug(f'Using GD OAuth token {token_file}')
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.debug('Requesting new GD OAuth token')
                    creds.refresh(Request())
                else:
                    raise Exception("Problem with creds - create the token again")

                # Save the credentials for the next run
                with open(token_file, 'w') as token:
                    logger.debug('Saving new GD OAuth token')
                    token.write(creds.to_json())
            else:
                logger.debug('GD OAuth Token valid')
        else:
            gd_service_account = config.service_account
            logger.debug(f'Using GD Service Account {gd_service_account}')
            creds = service_account.Credentials.from_service_account_file(gd_service_account, scopes=SCOPES)

        self.service = build('drive', 'v3', credentials=creds)

    def get_cdn_url(self, key):
        """
        only support files saved in a folder for GD
        S3 supports folder and all stored in the root
        """
        key = self.clean_key(key)

        full_name = os.path.join(self.folder, key)
        parent_id, folder_id = self.root_folder_id, None
        path_parts = full_name.split(os.path.sep)
        filename = path_parts[-1]
        logger.info(f"looking for folders for {path_parts[0:-1]} before uploading {filename=}")
        for folder in path_parts[0:-1]:
            folder_id = self._get_id_from_parent_and_name(parent_id, folder, use_mime_type=True, raise_on_missing=True)
            parent_id = folder_id

        # get id of file inside folder (or sub folder)
        file_id = self._get_id_from_parent_and_name(folder_id, filename)
        return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

    def exists(self, key):
        try:
            self.get_cdn_url(key)
            return True
        except: return False

    def uploadf(self, file: str, key: str, **_kwargs):
        """
        1. for each sub-folder in the path check if exists or create
        2. upload file to root_id/other_paths.../filename
        """
        key = self.clean_key(key)

        full_name = os.path.join(self.folder, key)
        parent_id, upload_to = self.root_folder_id, None
        path_parts = full_name.split(os.path.sep)
        filename = path_parts[-1]
        logger.info(f"checking folders {path_parts[0:-1]} exist (or creating) before uploading {filename=}")
        for folder in path_parts[0:-1]:
            upload_to = self._get_id_from_parent_and_name(parent_id, folder, use_mime_type=True, raise_on_missing=False)
            if upload_to is None:
                upload_to = self._mkdir(folder, parent_id)
            parent_id = upload_to

        # upload file to gd
        logger.debug(f'uploading {filename=} to folder id {upload_to}')
        file_metadata = {
            'name': [filename],
            'parents': [upload_to]
        }
        media = MediaFileUpload(file, resumable=True)
        gd_file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logger.debug(f'uploadf: uploaded file {gd_file["id"]} succesfully in folder={upload_to}')

    def upload(self, filename: str, key: str, **kwargs):
        # GD only requires the filename not a file reader
        self.uploadf(filename, key, **kwargs)

    def clean_key(self, key):
        # GDrive does not work well with trailing forward slashes and some keys come with that
        if key.startswith('/'):
            logger.debug(f'Found and fixed a leading "/" for {key=}')
            return key[1:]
        return key

    # gets the Drive folderID if it is there
    def _get_id_from_parent_and_name(self, parent_id: str, name: str, retries: int = 1, sleep_seconds: int = 10, use_mime_type: bool = False, raise_on_missing: bool = True, use_cache=False):
        """
        Retrieves the id of a folder or file from its @name and the @parent_id folder
        Optionally does multiple @retries and sleeps @sleep_seconds between them
        If @use_mime_type will restrict search to "mimeType='application/vnd.google-apps.folder'"
        If @raise_on_missing will throw error when not found, or returns None
        Will remember previous calls to avoid duplication if @use_cache
        DM - caching giving a perf improvement in order of 41s to 46s
          So I prefer not to use yet, purely as caching notoriously hard in terms of edge cases
          and pro's don't outweigh cons for me (yet)
          to be fair I just need to test this and make sure it always runs well!
        Returns the id of the file or folder from its name as a string
        """
        # cache logic
        if use_cache:
            self.api_cache = getattr(self, "api_cache", {})
            cache_key = f"{parent_id}_{name}_{use_mime_type}"
            if cache_key in self.api_cache:
                logger.debug(f"cache hit for {cache_key=}")
                return self.api_cache[cache_key]

        # API logic
        debug_header: str = f"[searching {name=} in {parent_id=}]"
        query_string = f"'{parent_id}' in parents and name = '{name}' and trashed = false "
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
                _id = items[-1]['id']
                if use_cache: self.api_cache[cache_key] = _id
                return _id
            else:
                logger.debug(f'{debug_header} not found, attempt {attempt+1}/{retries}.')
                if attempt < retries - 1:
                    logger.debug(f'sleeping for {sleep_seconds} second(s)')
                    time.sleep(sleep_seconds)

        if raise_on_missing:
            raise ValueError(f'{debug_header} not found after {retries} attempt(s)')
        return None

    def _mkdir(self, name: str, parent_id: str):
        """
        Creates a new GDrive folder @name inside folder @parent_id
        Returns id of the created folder
        """
        logger.debug(f'Creating new folder with {name=} inside {parent_id=}')
        file_metadata = {
            'name': [name],
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        gd_folder = self.service.files().create(body=file_metadata, fields='id').execute()
        return gd_folder.get('id')
