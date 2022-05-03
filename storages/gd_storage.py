# import boto3
# from botocore.errorfactory import ClientError
from loguru import logger
from .base_storage import Storage
from dataclasses import dataclass

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account


@dataclass
class GDConfig:
    bucket: str
    region: str
    key: str
    secret: str
    folder: str = ""
    private: bool = False


class GDStorage(Storage):

    def __init__(self, config: GDConfig):
        self.bucket = config.bucket
        self.region = config.region
        self.folder = config.folder
        self.private = config.private

        SCOPES = ['https://www.googleapis.com/auth/drive']

        creds = service_account.Credentials.from_service_account_file('service_account.json', scopes=SCOPES)

        self.service = build('drive', 'v3', credentials=creds)

            # if len(self.folder) and self.folder[-1] != '/':
        #     self.folder += '/'

        # self.s3 = boto3.client(
        #     's3',
        #     region_name=self.region,
        #     endpoint_url=f'https://{self.region}.digitaloceanspaces.com',
        #     aws_access_key_id=config.key,
        #     aws_secret_access_key=config.secret
        # )

    def _get_path(self, key):
        return self.folder + key

    def get_cdn_url(self, key):
        # key will be SM0002/twitter__media_ExeUSW2UcAE6RbN.jpg

        directory = key.split('/', 1)[0]
        logger.debug(f'directory: {directory}')
        # eg twitter__media_asdf.jpg
        filename = key.split('/', 1)[1]
        logger.debug(f'filename: {filename}')


        # TODO put that back to CIR value!
        cir_faa_folder_id ='1ljwzoAdKdJMJzRW9gPHDC8fkRykVH83X'

        # need to lookup the id of folder eg SM0002 
        results = self.service.files().list(q=f"'{cir_faa_folder_id}' in parents \
                                            and name = '{directory}' ",
                                        spaces='drive', # ie not appDataFolder or photos
                                        fields='files(id, name)'
                                        ).execute()
        items = results.get('files', [])

        folder_id = None
        for item in items:
            logger.debug(f"found folder of {item['name']}")
            folder_id= item['id']

        if folder_id is None:
            raise ValueError('Cant find folder')

        # check for folder name in file eg youtube_dl_sDE-qZdi8p8/index.html'
        # happens doing thumbnails

        # will always return a and a blank b even if there is nothing to split
        a, _, b = filename.partition('/')

        if b != '':
            # a: 'youtube_dl_sDE-qZdi8p8'
            # b: 'index.html'
            logger.debug(f'xxxx need to split on a: {a} and {b}')

             

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
                raise ValueError('Problem finding folder')


        # get id of file inside folder (or sub folder)
        results = self.service.files().list(q=f"'{folder_id}' in parents \
                                            and name = '{filename}' ",
                                        spaces='drive', # ie not appDataFolder or photos
                                        fields='files(id, name)'
                                        ).execute()
        items = results.get('files', [])
        
        file_id = None
        for item in items:
            logger.debug(f"found file of {item['name']}")
            file_id= item['id']

        if file_id is None:
            raise ValueError('Problem finding file')
            
        foo = "https://drive.google.com/file/d/" + file_id + "/view?usp=sharing"

        return foo
        # return f'https://{self.bucket}.{self.region}.cdn.digitaloceanspaces.com/{self._get_path(key)}'

    def exists(self, key):
        # try:
        #     self.s3.head_object(Bucket=self.bucket, Key=self._get_path(key))
        #     return True
        # except ClientError:
        #     return False
        return False

    def uploadf(self, file, key, **kwargs):
        # if self.private:
        #     extra_args = kwargs.get("extra_args", {})
        # else:
        #     extra_args = kwargs.get("extra_args", {'ACL': 'public-read'})

        dm_hash_folder_id ='1ljwzoAdKdJMJzRW9gPHDC8fkRykVH83X'

        # Files auto-archiver (CIR and linked to dave@hmsoftware.co.uk)
        # cir_faa_folder_id ='1H2RWV89kSjjS2CJJjAF_YHW3kiXjxm69'
        # TODO put that back to CIR value!
        cir_faa_folder_id ='1ljwzoAdKdJMJzRW9gPHDC8fkRykVH83X'

        # Assuming using filenumber as a folder eg SM0002
        # key is 'SM0002/twitter__media_ExeUSW2UcAE6RbN.jpg'
        
        # split on first occurance of /
        # eg SM0005
        directory = key.split('/', 1)[0]
        # eg twitter__media_asdf.jpg
        filename = key.split('/', 1)[1]

         # does folder eg SM0005 exist already inside parent of Files auto-archiver
        results = self.service.files().list(q=f"'{cir_faa_folder_id}' in parents \
                                            and mimeType='application/vnd.google-apps.folder' \
                                            and name = '{directory}' ",
                                        spaces='drive', # ie not appDataFolder or photos
                                        fields='files(id, name)'
                                        ).execute()
        items = results.get('files', [])
        folder_id_to_upload_to = None
        if len(items) > 1:
            logger.error(f'Duplicate folder name of {directory} which should never happen')

        for item in items:
            logger.debug(f"Found existing folder of {item['name']}")
            folder_id_to_upload_to = item['id']

        if folder_id_to_upload_to is None:
            # create new folder
            file_metadata = {
                'name': [directory],
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [cir_faa_folder_id]
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
            logger.debug(f'need to split')

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
