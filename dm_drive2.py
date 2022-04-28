from google.oauth2 import service_account

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def main():
    # SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
    SCOPES = ['https://www.googleapis.com/auth/drive']

    creds = service_account.Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
        
    try:
        service = build('drive', 'v3', credentials=creds)

        # Call the Drive v3 API
        # results = service.files().list(pageSize=20, fields="nextPageToken, files(id, name)").execute()
        results = service.files().list().execute()
        items = results.get('files', [])

        if not items:
            print('No files found.')
            return

        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))
        
    except HttpError as error:
        # TODO(developer) - Handle errors from drive API.
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()