import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If creating for first time download the OAuth Client Ids json `credentials.json` from https://console.cloud.google.com/apis/credentials OAuth 2.0 Client IDs
# add "http://localhost:55192/" to the list of "Authorised redirect URIs"
# https://davemateer.com/2022/04/28/google-drive-with-python for more information

# You can run this code to get a new token and verify it belongs to the correct user
# This token will be refresh automatically by the auto-archiver

# Code below from https://developers.google.com/drive/api/quickstart/python

SCOPES = ['https://www.googleapis.com/auth/drive']


def main():
    token_file = 'gd-token.json'
    creds = None

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print('Requesting new token')
            creds.refresh(Request())
        else:
            print('First run through so putting up login dialog')
            # credentials.json downloaded from https://console.cloud.google.com/apis/credentials
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=55192)
        # Save the credentials for the next run
        with open(token_file, 'w') as token:
            print('Saving new token')
            token.write(creds.to_json())
    else:
        print('Token valid')

    try:
        service = build('drive', 'v3', credentials=creds)

        # About the user
        results = service.about().get(fields="*").execute()
        emailAddress = results['user']['emailAddress']
        print(emailAddress)

        # Call the Drive v3 API and return some files
        results = service.files().list(
            pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])

        if not items:
            print('No files found.')
            return
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))

    except HttpError as error:
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()
