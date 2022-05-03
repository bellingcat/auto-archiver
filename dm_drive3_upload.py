# from __future__ import print_function
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account


def upload_appdata():
    # creds, _ = google.auth.default()
    SCOPES = ['https://www.googleapis.com/auth/drive']

    creds = service_account.Credentials.from_service_account_file('service_account.json', scopes=SCOPES)

    try:
        service = build('drive', 'v3', credentials=creds)

        # 1. list all files and folders
        # results = service.files().list().execute()
        # items = results.get('files', [])

        # for item in items:
        #     print(u'{0} ({1})'.format(item['name'], item['id']))

        # 1.5. Upload photo.jpg image to folder
        # # Hash (davemateer@gmail.com) 
        dm_hash_folder_id ='1ljwzoAdKdJMJzRW9gPHDC8fkRykVH83X'
        # # Files auto-archiver (CIR and linked to dave@hmsoftware.co.uk)
        cir_faa_folder_id ='1H2RWV89kSjjS2CJJjAF_YHW3kiXjxm69'

        # file_metadata = {
        #     'name': 'photo.jpg',
        #     'parents': [folder_id]
        # }
        # media = MediaFileUpload('files/photo.jpg',
        #                         mimetype='image/jpeg',
        #                         resumable=True)
        # file = service.files().create(body=file_metadata,
        #                                     media_body=media,
        #                                     fields='id').execute()

        # # 2.upload anohter jpg
        # file_metadata = {
        #     'name': 'twitter__media_FMQg7yeXwAAwNEi.jpg',
        #     'parents': [folder_id]
        # }
        # media = MediaFileUpload('files/twitter__media_FMQg7yeXwAAwNEi.jpg',
        #                         # mimetype='image/jpeg',
        #                         resumable=True)
        # file = service.files().create(body=file_metadata,
        #                                     media_body=media,
        #                                     fields='id').execute()

        # # 3.upload html
        # file_metadata = {
        #     'name': 'index.html',
        #     'parents': [folder_id]
        # }
        # media = MediaFileUpload('files/index.html',
        #                         # mimetype='image/jpeg',
        #                         resumable=True)
        # file = service.files().create(body=file_metadata,
        #                                     media_body=media,
        #                                     fields='id').execute()
        # # 4.upload more html
        # filename = 'twitter__minmyatnaing13_status_1499415562937503751.html'
        # file_metadata = {
        #     'name': [filename],
        #     'parents': [folder_id]
        # }
        # media = MediaFileUpload('files/' + filename, resumable=True)
        # file = service.files().create(body=file_metadata,
        #                                     media_body=media,
        #                                     fields='id').execute()

        # # png
        # filename = 'youtube_dl__@user52610777_video_70170346222991639302022-04-29T07_25_32.069610.png'
        # file_metadata = {
        #     'name': [filename],
        #     'parents': [folder_id]
        # }
        # media = MediaFileUpload('files/' + filename, resumable=True)
        # file = service.files().create(body=file_metadata,
        #                                     media_body=media,
        #                                     fields='id').execute()
        # # mkv
        # filename = 'youtube_dl_343188674422293.mkv'
        # file_metadata = {
        #     'name': [filename],
        #     'parents': [folder_id]
        # }
        # media = MediaFileUpload('files/' + filename, resumable=True)
        # file = service.files().create(body=file_metadata,
        #                                     media_body=media,
        #                                     fields='id').execute()

        # # mp4
        # filename = 'youtube_dl_7017034622299163930.mp4'
        # file_metadata = {
        #     'name': [filename],
        #     'parents': [folder_id]
        # }
        # media = MediaFileUpload('files/' + filename, resumable=True)
        # file = service.files().create(body=file_metadata,
        #                                     media_body=media,
        #                                     fields='id').execute()

        # # webm
        # filename = 'youtube_dl_sDE-qZdi8p8.webm'
        # file_metadata = {
        #     'name': [filename],
        #     'parents': [folder_id]
        # }
        # media = MediaFileUpload('files/' + filename, resumable=True)
        # file = service.files().create(body=file_metadata,
        #                                     media_body=media,
        #                                     fields='id').execute()


        # 5. List only folders
        # results = service.files().list(q="mimeType='application/vnd.google-apps.folder'",
        #                                   spaces='drive', # ie not appDataFolder or photos
        #                                   fields='files(id, name)'
        #                                   ).execute()
        # items = results.get('files', [])

        # for item in items:
        #     foo = item['name'] + item['id']
        #     print(foo)

        # 6. List only folders within a folder (but not subfolders eg SM005 SM006 but not Subfolder inside SM0005)
        # results = service.files().list(q="'1H2RWV89kSjjS2CJJjAF_YHW3kiXjxm69' in parents",
        results = service.files().list(q=f"'{dm_hash_folder_id}' in parents \
                                            and mimeType='application/vnd.google-apps.folder' ",
                                          spaces='drive', # ie not appDataFolder or photos
                                          fields='files(id, name)'
                                          ).execute()
        items = results.get('files', [])

        # for item in items:
        #     foo = item['name'] + " " + item['id']
        #     print(foo)

        # 7. Does folder exist within a folder eg SM0005 inside hash and get ID if it does
        results = service.files().list(q=f"'{dm_hash_folder_id}' in parents \
                                            and mimeType='application/vnd.google-apps.folder' \
                                            and name = 'SM0005' ",
                                          spaces='drive', # ie not appDataFolder or photos
                                          fields='files(id, name)'
                                          ).execute()
        items = results.get('files', [])
        for item in items:
            foo = item['name'] + " " + item['id']
            print(foo)


        # 8. Create folder within Files auto-archiver shared folder
        # file_metadata = {
        #     'name': 'foo',
        #     'mimeType': 'application/vnd.google-apps.folder',
        #     'parents': [folder_id]
        # }
        # file = service.files().create(body=file_metadata, fields='id').execute()
        # new_folder_id = file.get('id')

        # Upload file to newly created folder
        # filename = 'youtube_dl_sDE-qZdi8p8.webm'
        # file_metadata = {
        #     'name': [filename],
        #     'parents': [new_folder_id]
        # }
        # media = MediaFileUpload('files/' + filename, resumable=True)
        # file = service.files().create(body=file_metadata,
        #                                     media_body=media,
        #                                     fields='id').execute()

        # does folder exist already inside parent of Files auto-archiver
        
        # 
        # List and do paging

    except HttpError as error:
        print(F'An error occurred: {error}')
        file = None

    # return file.get('id')


if __name__ == '__main__':
    upload_appdata()

        # create a file in a new folder
        # file_metadata = {
        #     'name': 'Invoices',
        #     'mimeType': 'application/vnd.google-apps.folder'
        # }
        # file = service.files().create(body=file_metadata,
        #                                     fields='id').execute()
        # print('Folder ID: %s' % file.get('id'))

        # upload an image
        # file_metadata = {'name': 'photo.jpg'}
        # media = MediaFileUpload('files/photo.jpg',
        #                         mimetype='image/jpeg')
        # file = service.files().create(body=file_metadata,
        #                                     media_body=media,
        #                                     fields='id').execute()
        # id = file.get('id')
        # print(f'id: {id}')


        # print 'File ID: %s' % file.get('id')

        # pylint: disable=maybe-no-member
        # file_metadata = {
        #     'name': 'abc.txt',
        #     'parents': ['appDataFolder']
        # }
        # media = MediaFileUpload('abc.txt',
        #                         mimetype='text/txt',
        #                         resumable=True)
        # file = service.files().create(body=file_metadata, media_body=media,
        #                               fields='id').execute()
        # print(F'File ID: {file.get("id")}')
