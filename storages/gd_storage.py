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

class GDStorage(Storage):

    def __init__(self, config: GDConfig):
        self.root_folder_id = config.root_folder_id
        SCOPES = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
        self.service = build('drive', 'v3', credentials=creds)

    def _get_path(self, key):
        return self.folder + key

    def get_cdn_url(self, key):
        # only support files saved in a folders for GD
        # S3 supports folder and all stored in the root

        # key will be SM0002/twitter__media_ExeUSW2UcAE6RbN.jpg
        foldername = key.split('/', 1)[0]
        # eg twitter__media_asdf.jpg
        filename = key.split('/', 1)[1]

        logger.debug(f'Looking for {foldername} and filename: {filename} on GD')

        # retry policy on Google Drive
        try_again = True
        counter = 1
        folder_id = None
        while try_again:
            # need to lookup the id of folder eg SM0002 which should be there already as this is get_cdn_url
            results = self.service.files().list(q=f"'{self.root_folder_id}' in parents \
                                                and name = '{foldername}' ",
                                            spaces='drive', # ie not appDataFolder or photos
                                            fields='files(id, name)'
                                            ).execute()
            items = results.get('files', [])

            for item in items:
                logger.debug(f"found folder of {item['name']}")
                folder_id= item['id']
                try_again = False

            if folder_id is None:
                logger.debug(f'Cant find {foldername=} waiting and trying again {counter=}')
                counter += 1
                time.sleep(10)
                if counter > 18:
                    raise ValueError(f'Cant find  {foldername} and retried 18 times pausing 10seconds at a time which is 3 minutes')

        # check for sub folder in file eg youtube_dl_sDE-qZdi8p8/index.html'
        # happens doing thumbnails
        a, _, b = filename.partition('/')

        if b != '':
            # a: 'youtube_dl_sDE-qZdi8p8'
            # b: 'index.html'
            logger.debug(f'get_cdn_url: Found a subfolder so need to split on a: {a} and {b}')

            # get id of the sub folder
            results = self.service.files().list(q=f"'{folder_id}' in parents \
                                                and mimeType='application/vnd.google-apps.folder' \
                                                and name = '{a}' ",
                                            spaces='drive', # ie not appDataFolder or photos
                                            fields='files(id, name)'
                                            ).execute()
            items = results.get('files', [])

            filename = None
            for item in items:
                folder_id = item['id']
                filename = b
            if filename is None:
                raise ValueError(f'Problem finding sub folder {a}')

        # get id of file inside folder (or sub folder)
        results = self.service.files().list(q=f"'{folder_id}' in parents \
                                            and name = '{filename}' ",
                                        spaces='drive', 
                                        fields='files(id, name)'
                                        ).execute()
        items = results.get('files', [])
        
        file_id = None
        for item in items:
            logger.debug(f"found file of {item['name']}")
            file_id= item['id']

        if file_id is None:
            raise ValueError(f'Problem finding file {filename} in folder_id {folder_id}')
            
        foo = "https://drive.google.com/file/d/" + file_id + "/view?usp=sharing"
        return foo

    def exists(self, key):
        # Not implemented yet
        # Google drive will accept duplicate named filenames as it is stored as a different fileid 

        # try:
        #     self.s3.head_object(Bucket=self.bucket, Key=self._get_path(key))
        #     return True
        # except ClientError:
        #     return False
        return False

    def uploadf(self, file, key, **kwargs):
        # split on first occurance of /
        # eg SM0005
        foldername = key.split('/', 1)[0]
        # eg twitter__media_asdf.jpg
        filename = key.split('/', 1)[1]

         # does folder eg SM0005 exist already inside parent of Files auto-archiver
        results = self.service.files().list(q=f"'{self.root_folder_id}' in parents \
                                            and mimeType='application/vnd.google-apps.folder' \
                                            and name = '{foldername}' ",
                                        spaces='drive', 
                                        fields='files(id, name)'
                                        ).execute()
        items = results.get('files', [])
        folder_id_to_upload_to = None
        if len(items) > 1:
            logger.error(f'Duplicate folder name of {foldername} which should never happen, but continuing anyway')

        for item in items:
            logger.debug(f"Found existing folder of {item['name']}")
            folder_id_to_upload_to = item['id']

        if folder_id_to_upload_to is None:
            logger.debug(f'Creating new folder {foldername}')
            file_metadata = {
                'name': [foldername],
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.root_folder_id]
            }
            gd_file = self.service.files().create(body=file_metadata, fields='id').execute()
            folder_id_to_upload_to = gd_file.get('id')
        
        # check for subfolder nema in file eg youtube_dl_sDE-qZdi8p8/out1.jpg'
        # happens doing thumbnails

        # will always return a and a blank b even if there is nothing to split
        # https://stackoverflow.com/a/38149500/26086
        a, _, b = filename.partition('/')

        if b != '':
            # a: 'youtube_dl_sDE-qZdi8p8'
            # b: 'out1.jpg'
            logger.debug(f'uploadf: Found a subfolder so need to split on a: {a} and {b}')

            # does the 'a' folder exist already in folder_id_to_upload_to eg SM0005
            results = self.service.files().list(q=f"'{folder_id_to_upload_to}' in parents \
                                                and mimeType='application/vnd.google-apps.folder' \
                                                and name = '{a}' ",
                                            spaces='drive', # ie not appDataFolder or photos
                                            fields='files(id, name)'
                                            ).execute()
            items = results.get('files', [])
            sub_folder_id_to_upload_to = None
            if len(items) > 1:
                logger.error(f'Duplicate folder name of {a} which should never happen')

            for item in items:
                logger.debug(f"Found existing folder of {item['name']}")
                sub_folder_id_to_upload_to = item['id']

            if sub_folder_id_to_upload_to is None:
                # create new folder
                file_metadata = {
                    'name': [a],
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [folder_id_to_upload_to]
                }
                gd_file = self.service.files().create(body=file_metadata, fields='id').execute()
                sub_folder_id_to_upload_to = gd_file.get('id')

            filename = b
            folder_id_to_upload_to = sub_folder_id_to_upload_to
            # back to normal control flow
            
        # else:
        # upload file to gd
        file_metadata = {
            # 'name': 'twitter__media_FMQg7yeXwAAwNEi.jpg',
            'name': [filename],
            'parents': [folder_id_to_upload_to]
        }
        media = MediaFileUpload(file, resumable=True)
        gd_file = self.service.files().create(body=file_metadata,
                                            media_body=media,
                                            fields='id').execute()
