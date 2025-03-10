import os.path
import click, json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# You can run this code to get a new token and verify it belongs to the correct user
# This token will be refresh automatically by the auto-archiver
# Code below from https://developers.google.com/drive/api/quickstart/python
# Example invocation: py scripts/create_update_gdrive_oauth_token.py -c secrets/credentials.json -t secrets/gd-token.json

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


@click.command(
    help="script to generate Google Drive OAuth token to use gdrive_storage, requires credentials.json and outputs gd-token.json, if you don't have credentials.json go to https://console.cloud.google.com/apis/credentials. Be sure to add 'http://localhost:55192/' to the Authorized redirect URIs in your OAuth App. More info:  https://davemateer.com/2022/04/28/google-drive-with-python"
)
@click.option(
    "--credentials",
    "-c",
    type=click.Path(exists=True),
    help="path to the credentials.json file downloaded from https://console.cloud.google.com/apis/credentials",
    required=True,
)
@click.option(
    "--token",
    "-t",
    type=click.Path(exists=False),
    default="gd-token.json",
    help="file where to place the OAuth token, defaults to gd-token.json which you must then move to where your orchestration file points to, defaults to gd-token.json",
    required=True,
)
def main(credentials, token):
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    creds = None
    if os.path.exists(token):
        with open(token, "r") as stream:
            creds_json = json.load(stream)
            # creds = Credentials.from_authorized_user_file(creds_json, SCOPES)
            creds_json["refresh_token"] = creds_json.get("refresh_token", "")
            creds = Credentials.from_authorized_user_info(creds_json, SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Requesting new token")
            creds.refresh(Request())
        else:
            print("First run through so putting up login dialog")
            # credentials.json downloaded from https://console.cloud.google.com/apis/credentials
            flow = InstalledAppFlow.from_client_secrets_file(credentials, SCOPES)
            creds = flow.run_local_server(port=55192)
        # Save the credentials for the next run
        with open(token, "w") as token:
            print("Saving new token")
            token.write(creds.to_json())
    else:
        print("Token valid")

    try:
        service = build("drive", "v3", credentials=creds)

        # About the user
        results = service.about().get(fields="*").execute()
        emailAddress = results["user"]["emailAddress"]
        print(emailAddress)

        # Call the Drive v3 API and return some files
        results = service.files().list(pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get("files", [])

        if not items:
            print("No files found.")
            return
        print("Files:")
        for item in items:
            print("{0} ({1})".format(item["name"], item["id"]))

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
