{
    "name": "Google Drive Storage",
    "type": ["storage"],
    "author": "Dave Mateer",
    "entry_point": "gdrive_storage::GDriveStorage",
    "requires_setup": True,
    "dependencies": {
        "python": [
            "loguru",
            "googleapiclient",
            "google",
        ],
    },
    "configs": {
        "path_generator": {
            "default": "url",
            "help": "how to store the file in terms of directory structure: 'flat' sets to root; 'url' creates a directory based on the provided URL; 'random' creates a random directory.",
            "choices": ["flat", "url", "random"],
        },
        "filename_generator": {
            "default": "static",
            "help": "how to name stored files: 'random' creates a random string; 'static' uses a hash, with the settings of the 'hash_enricher' module (defaults to SHA256 if not enabled).",
            "choices": ["random", "static"],
        },
        "root_folder_id": {
            "required": True,
            "help": "root google drive folder ID to use as storage, found in URL: 'https://drive.google.com/drive/folders/FOLDER_ID'",
        },
        "oauth_token": {
            "default": None,
            "help": "JSON filename with Google Drive OAuth token: check auto-archiver repository scripts folder for create_update_gdrive_oauth_token.py. NOTE: storage used will count towards owner of GDrive folder, therefore it is best to use oauth_token_filename over service_account.",
        },
        "service_account": {
            "default": "secrets/service_account.json",
            "help": "service account JSON file path, same as used for Google Sheets. NOTE: storage used will count towards the developer account.",
        },
    },
    "description": """
    
    GDriveStorage: A storage module for saving archived content to Google Drive.

    Source Documentation: https://davemateer.com/2022/04/28/google-drive-with-python

    ### Features
    - Saves media files to Google Drive, organizing them into folders based on the provided path structure.
    - Supports OAuth token-based authentication or service account credentials for API access.
    - Automatically creates folders in Google Drive if they don't exist.
    - Retrieves CDN URLs for stored files, enabling easy sharing and access.

    ### Notes
    - Requires setup with either a Google OAuth token or a service account JSON file.
    - Files are uploaded to the specified `root_folder_id` and organized by the `media.key` structure.
    - Automatically handles Google Drive API token refreshes for long-running jobs.
    
    ## Overview
This module integrates Google Drive as a storage backend, enabling automatic folder creation and file uploads. It supports authentication via **service accounts** (recommended for automation) or **OAuth tokens** (for user-based authentication).

## Features
- Saves files to Google Drive, organizing them into structured folders.
- Supports both **service account** and **OAuth token** authentication.
- Automatically creates folders if they don't exist.
- Generates public URLs for easy file sharing.

## Setup Guide
1. **Enable Google Drive API**
   - Create a Google Cloud project at [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the **Google Drive API**.

2. **Set Up a Google Drive Folder**
   - Create a folder in **Google Drive** and copy its **folder ID** from the URL.
   - Add the **folder ID** to your configuration (`orchestration.yaml`):
     ```yaml
     root_folder_id: "FOLDER_ID"
     ```

3. **Authentication Options**
   - **Option 1: Service Account (Recommended)**
     - Create a **service account** in Google Cloud IAM.
     - Download the JSON key file and save it as:
       ```
       secrets/service_account.json
       ```
     - **Share your Drive folder** with the service account’s `client_email` (found in the JSON file).
     
   - **Option 2: OAuth Token (User Authentication)**
     - Create OAuth **Desktop App credentials** in Google Cloud.
     - Save the credentials as:
       ```
       secrets/oauth_credentials.json
       ```
     - Generate an OAuth token by running:
       ```sh
       python scripts/create_update_gdrive_oauth_token.py -c secrets/oauth_credentials.json
       ```

    
    Notes on the OAuth token:
    Tokens are refreshed after 1 hour however keep working for 7 days (tbc)
    so as long as the job doesn't last for 7 days then this method of refreshing only once per run will work
    see this link for details on the token:
    https://davemateer.com/2022/04/28/google-drive-with-python#tokens
    
    
""",
}
