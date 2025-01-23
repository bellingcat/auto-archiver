m = {
    "name": "Google Drive Storage",
    "type": ["storage"],
    "requires_setup": True,
    "external_dependencies": {
        "python": [
            "loguru",
            "google-api-python-client",
            "google-auth",
            "google-auth-oauthlib",
            "google-auth-httplib2"
        ],
    },
    "configs": {
            "path_generator": {
                "default": "url",
                "help": "how to store the file in terms of directory structure: 'flat' sets to root; 'url' creates a directory based on the provided URL; 'random' creates a random directory.",
            },
            "filename_generator": {
                "default": "random",
                "help": "how to name stored files: 'random' creates a random string; 'static' uses a replicable strategy such as a hash.",
            },
        # TODO: get base storage configs
        "root_folder_id": {"default": None, "help": "root google drive folder ID to use as storage, found in URL: 'https://drive.google.com/drive/folders/FOLDER_ID'"},
        "oauth_token": {"default": None, "help": "JSON filename with Google Drive OAuth token: check auto-archiver repository scripts folder for create_update_gdrive_oauth_token.py. NOTE: storage used will count towards owner of GDrive folder, therefore it is best to use oauth_token_filename over service_account."},
        "service_account": {"default": "secrets/service_account.json", "help": "service account JSON file path, same as used for Google Sheets. NOTE: storage used will count towards the developer account."},
    },
    "description": """
    GDriveStorage: A storage module for saving archived content to Google Drive.

    ### Features
    - Saves media files to Google Drive, organizing them into folders based on the provided path structure.
    - Supports OAuth token-based authentication or service account credentials for API access.
    - Automatically creates folders in Google Drive if they don't exist.
    - Retrieves CDN URLs for stored files, enabling easy sharing and access.

    ### Notes
    - Requires setup with either a Google OAuth token or a service account JSON file.
    - Files are uploaded to the specified `root_folder_id` and organized by the `media.key` structure.
    - Automatically handles Google Drive API token refreshes for long-running jobs.
    """
}
