
from __future__ import print_function

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account


def upload_appdata():
    # creds, _ = google.auth.default()
    SCOPES = ['https://www.googleapis.com/auth/drive']

    creds = service_account.Credentials.from_service_account_file('service_account.json', scopes=SCOPES)

    try:
        # call drive api client
        service = build('drive', 'v3', credentials=creds)

        # create a file in a new folder
        # file_metadata = {
        #     'name': 'Invoices',
        #     'mimeType': 'application/vnd.google-apps.folder'
        # }
        # file = service.files().create(body=file_metadata,
        #                                     fields='id').execute()
        # print('Folder ID: %s' % file.get('id'))

        # upload an image
        file_metadata = {'name': 'photo.jpg'}
        media = MediaFileUpload('files/photo.jpg',
                                mimetype='image/jpeg')
        file = service.files().create(body=file_metadata,
                                            media_body=media,
                                            fields='id').execute()
        id = file.get('id')
        print(f'id: {id}')

        # list files and folders
        results = service.files().list().execute()
        items = results.get('files', [])

        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))

        # upload an image to a folder
        folder_id ='1ljwzoAdKdJMJzRW9gPHDC8fkRykVH83X'
        file_metadata = {
            'name': 'photo.jpg',
            'parents': [folder_id]
        }
        media = MediaFileUpload('files/photo.jpg',
                                mimetype='image/jpeg',
                                resumable=True)
        file = service.files().create(body=file_metadata,
                                            media_body=media,
                                            fields='id').execute()

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

    except HttpError as error:
        print(F'An error occurred: {error}')
        file = None

    return file.get('id')


if __name__ == '__main__':
    upload_appdata()