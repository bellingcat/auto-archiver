Configs
=======

This section documents all configuration options available for various components.

InstagramAPIArchiver
--------------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - access_token
     - None
     - a valid instagrapi-api token
   * - api_endpoint
     - None
     - API endpoint to use
   * - full_profile
     - False
     - if true, will download all posts, tagged posts, stories, and highlights for a profile, if false, will only download the profile pic and information.
   * - full_profile_max_posts
     - 0
     - Use to limit the number of posts to download when full_profile is true. 0 means no limit. limit is applied softly since posts are fetched in batch, once to: posts, tagged posts, and highlights
   * - minimize_json_output
     - True
     - if true, will remove empty values from the json output

InstagramArchiver
-----------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - username
     - None
     - a valid Instagram username
   * - password
     - None
     - the corresponding Instagram account password
   * - download_folder
     - instaloader
     - name of a folder to temporarily download content to
   * - session_file
     - secrets/instaloader.session
     - path to the instagram session which saves session credentials

InstagramTbotArchiver
---------------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - api_id
     - None
     - telegram API_ID value, go to https://my.telegram.org/apps
   * - api_hash
     - None
     - telegram API_HASH value, go to https://my.telegram.org/apps
   * - session_file
     - secrets/anon-insta
     - optional, records the telegram login session for future usage, '.session' will be appended to the provided value.
   * - timeout
     - 45
     - timeout to fetch the instagram content in seconds.

TelethonArchiver
----------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - api_id
     - None
     - telegram API_ID value, go to https://my.telegram.org/apps
   * - api_hash
     - None
     - telegram API_HASH value, go to https://my.telegram.org/apps
   * - bot_token
     - None
     - optional, but allows access to more content such as large videos, talk to @botfather
   * - session_file
     - secrets/anon
     - optional, records the telegram login session for future usage, '.session' will be appended to the provided value.
   * - join_channels
     - True
     - disables the initial setup with channel_invites config, useful if you have a lot and get stuck
   * - channel_invites
     - {}
     - (JSON string) private channel invite links (format: t.me/joinchat/HASH OR t.me/+HASH) and (optional but important to avoid hanging for minutes on startup) channel id (format: CHANNEL_ID taken from a post url like https://t.me/c/CHANNEL_ID/1), the telegram account will join any new channels on setup

TwitterApiArchiver
------------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - bearer_token
     - None
     - [deprecated: see bearer_tokens] twitter API bearer_token which is enough for archiving, if not provided you will need consumer_key, consumer_secret, access_token, access_secret
   * - bearer_tokens
     - []
     -  a list of twitter API bearer_token which is enough for archiving, if not provided you will need consumer_key, consumer_secret, access_token, access_secret, if provided you can still add those for better rate limits. CSV of bearer tokens if provided via the command line
   * - consumer_key
     - None
     - twitter API consumer_key
   * - consumer_secret
     - None
     - twitter API consumer_secret
   * - access_token
     - None
     - twitter API access_token
   * - access_secret
     - None
     - twitter API access_secret

VkArchiver
----------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - username
     - None
     - valid VKontakte username
   * - password
     - None
     - valid VKontakte password
   * - session_file
     - secrets/vk_config.v2.json
     - valid VKontakte password

YoutubeDLArchiver
-----------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - facebook_cookie
     - None
     - optional facebook cookie to have more access to content, from browser, looks like 'cookie: datr= xxxx'
   * - subtitles
     - True
     - download subtitles if available
   * - comments
     - False
     - download all comments if available, may lead to large metadata
   * - livestreams
     - False
     - if set, will download live streams, otherwise will skip them; see --max-filesize for more control
   * - live_from_start
     - False
     - if set, will download live streams from their earliest available moment, otherwise starts now.
   * - proxy
     - 
     - http/socks (https seems to not work atm) proxy to use for the webdriver, eg https://proxy- user:password@proxy-ip:port
   * - end_means_success
     - True
     - if True, any archived content will mean a 'success', if False this archiver will not return a 'success' stage; this is useful for cases when the yt-dlp will archive a video but ignore other types of content like images or text only pages that the subsequent archivers can retrieve.
   * - allow_playlist
     - False
     - If True will also download playlists, set to False if the expectation is to download a single video.
   * - max_downloads
     - inf
     - Use to limit the number of videos to download when a channel or long page is being extracted. 'inf' means no limit.
   * - cookies_from_browser
     - None
     - optional browser for ytdl to extract cookies from, can be one of: brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale
   * - cookie_file
     - None
     - optional cookie file to use for Youtube, see instructions here on how to export from your browser: https://github.com/yt-dlp/yt- dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp

AAApiDb
-------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - api_endpoint
     - None
     - API endpoint where calls are made to
   * - api_token
     - None
     - API Bearer token.
   * - public
     - False
     - whether the URL should be publicly available via the API
   * - author_id
     - None
     - which email to assign as author
   * - group_id
     - None
     - which group of users have access to the archive in case public=false as author
   * - allow_rearchive
     - True
     - if False then the API database will be queried prior to any archiving operations and stop if the link has already been archived
   * - store_results
     - True
     - when set, will send the results to the API database.
   * - tags
     - []
     - what tags to add to the archived URL

AtlosDb
-------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - api_token
     - None
     - An Atlos API token. For more information, see https://docs.atlos.org/technical/api/
   * - atlos_url
     - https://platform.atlos.org
     - The URL of your Atlos instance (e.g., https://platform.atlos.org), without a trailing slash.

CSVDb
-----

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - csv_file
     - db.csv
     - CSV file name

HashEnricher
------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - algorithm
     - SHA-256
     - hash algorithm to use
   * - chunksize
     - 16000000
     - number of bytes to use when reading files in chunks (if this value is too large you will run out of RAM), default is 16MB

ScreenshotEnricher
------------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - width
     - 1280
     - width of the screenshots
   * - height
     - 720
     - height of the screenshots
   * - timeout
     - 60
     - timeout for taking the screenshot
   * - sleep_before_screenshot
     - 4
     - seconds to wait for the pages to load before taking screenshot
   * - http_proxy
     - 
     - http proxy to use for the webdriver, eg http://proxy-user:password@proxy-ip:port
   * - save_to_pdf
     - False
     - save the page as pdf along with the screenshot. PDF saving options can be adjusted with the 'print_options' parameter
   * - print_options
     - {}
     - options to pass to the pdf printer

SSLEnricher
-----------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - skip_when_nothing_archived
     - True
     - if true, will skip enriching when no media is archived

ThumbnailEnricher
-----------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - thumbnails_per_minute
     - 60
     - how many thumbnails to generate per minute of video, can be limited by max_thumbnails
   * - max_thumbnails
     - 16
     - limit the number of thumbnails to generate per video, 0 means no limit

TimestampingEnricher
--------------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - tsa_urls
     - ['http://timestamp.digicert.com', 'http://timestamp.identrust.com', 'http://timestamp.globalsign.com/tsa/r6advanced1', 'http://tss.accv.es:8318/tsa']
     - List of RFC3161 Time Stamp Authorities to use, separate with commas if passed via the command line.

WaczArchiverEnricher
--------------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - profile
     - None
     - browsertrix-profile (for profile generation see https://github.com/webrecorder/browsertrix- crawler#creating-and-using-browser-profiles).
   * - docker_commands
     - None
     - if a custom docker invocation is needed
   * - timeout
     - 120
     - timeout for WACZ generation in seconds
   * - extract_media
     - False
     - If enabled all the images/videos/audio present in the WACZ archive will be extracted into separate Media and appear in the html report. The .wacz file will be kept untouched.
   * - extract_screenshot
     - True
     - If enabled the screenshot captured by browsertrix will be extracted into separate Media and appear in the html report. The .wacz file will be kept untouched.
   * - socks_proxy_host
     - None
     - SOCKS proxy host for browsertrix-crawler, use in combination with socks_proxy_port. eg: user:password@host
   * - socks_proxy_port
     - None
     - SOCKS proxy port for browsertrix-crawler, use in combination with socks_proxy_host. eg 1234
   * - proxy_server
     - None
     - SOCKS server proxy URL, in development

WaybackArchiverEnricher
-----------------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - timeout
     - 15
     - seconds to wait for successful archive confirmation from wayback, if more than this passes the result contains the job_id so the status can later be checked manually.
   * - if_not_archived_within
     - None
     - only tell wayback to archive if no archive is available before the number of seconds specified, use None to ignore this option. For more information: https://docs.google.com/document/d/1N sv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA
   * - key
     - None
     - wayback API key. to get credentials visit https://archive.org/account/s3.php
   * - secret
     - None
     - wayback API secret. to get credentials visit https://archive.org/account/s3.php
   * - proxy_http
     - None
     - http proxy to use for wayback requests, eg http://proxy-user:password@proxy-ip:port
   * - proxy_https
     - None
     - https proxy to use for wayback requests, eg https://proxy-user:password@proxy-ip:port

WhisperEnricher
---------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - api_endpoint
     - None
     - WhisperApi api endpoint, eg: https://whisperbox- api.com/api/v1, a deployment of https://github.com/bellingcat/whisperbox- transcribe.
   * - api_key
     - None
     - WhisperApi api key for authentication
   * - include_srt
     - False
     - Whether to include a subtitle SRT (SubRip Subtitle file) for the video (can be used in video players).
   * - timeout
     - 90
     - How many seconds to wait at most for a successful job completion.
   * - action
     - translate
     - which Whisper operation to execute

AtlosFeeder
-----------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - api_token
     - None
     - An Atlos API token. For more information, see https://docs.atlos.org/technical/api/
   * - atlos_url
     - https://platform.atlos.org
     - The URL of your Atlos instance (e.g., https://platform.atlos.org), without a trailing slash.

CLIFeeder
---------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - urls
     - None
     - URL(s) to archive, either a single URL or a list of urls, should not come from config.yaml

GsheetsFeeder
-------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - sheet
     - None
     - name of the sheet to archive
   * - sheet_id
     - None
     - (alternative to sheet name) the id of the sheet to archive
   * - header
     - 1
     - index of the header row (starts at 1)
   * - service_account
     - secrets/service_account.json
     - service account JSON file path
   * - columns
     - {'url': 'link', 'status': 'archive status', 'folder': 'destination folder', 'archive': 'archive location', 'date': 'archive date', 'thumbnail': 'thumbnail', 'timestamp': 'upload timestamp', 'title': 'upload title', 'text': 'text content', 'screenshot': 'screenshot', 'hash': 'hash', 'pdq_hash': 'perceptual hashes', 'wacz': 'wacz', 'replaywebpage': 'replaywebpage'}
     - names of columns in the google sheet (stringified JSON object)
   * - allow_worksheets
     - set()
     - (CSV) only worksheets whose name is included in allow are included (overrides worksheet_block), leave empty so all are allowed
   * - block_worksheets
     - set()
     - (CSV) explicitly block some worksheets from being processed
   * - use_sheet_names_in_stored_paths
     - True
     - if True the stored files path will include 'workbook_name/worksheet_name/...'

HtmlFormatter
-------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - detect_thumbnails
     - True
     - if true will group by thumbnails generated by thumbnail enricher by id 'thumbnail_00'

AtlosStorage
------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - path_generator
     - url
     - how to store the file in terms of directory structure: 'flat' sets to root; 'url' creates a directory based on the provided URL; 'random' creates a random directory.
   * - filename_generator
     - random
     - how to name stored files: 'random' creates a random string; 'static' uses a replicable strategy such as a hash.
   * - api_token
     - None
     - An Atlos API token. For more information, see https://docs.atlos.org/technical/api/
   * - atlos_url
     - https://platform.atlos.org
     - The URL of your Atlos instance (e.g., https://platform.atlos.org), without a trailing slash.

GDriveStorage
-------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - path_generator
     - url
     - how to store the file in terms of directory structure: 'flat' sets to root; 'url' creates a directory based on the provided URL; 'random' creates a random directory.
   * - filename_generator
     - random
     - how to name stored files: 'random' creates a random string; 'static' uses a replicable strategy such as a hash.
   * - root_folder_id
     - None
     - root google drive folder ID to use as storage, found in URL: 'https://drive.google.com/drive/folders/FOLDER_ID'
   * - oauth_token
     - None
     - JSON filename with Google Drive OAuth token: check auto-archiver repository scripts folder for create_update_gdrive_oauth_token.py. NOTE: storage used will count towards owner of GDrive folder, therefore it is best to use oauth_token_filename over service_account.
   * - service_account
     - secrets/service_account.json
     - service account JSON file path, same as used for Google Sheets. NOTE: storage used will count towards the developer account.

LocalStorage
------------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - path_generator
     - url
     - how to store the file in terms of directory structure: 'flat' sets to root; 'url' creates a directory based on the provided URL; 'random' creates a random directory.
   * - filename_generator
     - random
     - how to name stored files: 'random' creates a random string; 'static' uses a replicable strategy such as a hash.
   * - save_to
     - ./archived
     - folder where to save archived content
   * - save_absolute
     - False
     - whether the path to the stored file is absolute or relative in the output result inc. formatters (WARN: leaks the file structure)

S3Storage
---------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - path_generator
     - url
     - how to store the file in terms of directory structure: 'flat' sets to root; 'url' creates a directory based on the provided URL; 'random' creates a random directory.
   * - filename_generator
     - random
     - how to name stored files: 'random' creates a random string; 'static' uses a replicable strategy such as a hash.
   * - bucket
     - None
     - S3 bucket name
   * - region
     - None
     - S3 region name
   * - key
     - None
     - S3 API key
   * - secret
     - None
     - S3 API secret
   * - random_no_duplicate
     - False
     - if set, it will override `path_generator`, `filename_generator` and `folder`. It will check if the file already exists and if so it will not upload it again. Creates a new root folder path `no-dups/`
   * - endpoint_url
     - https://{region}.digitaloceanspaces.com
     - S3 bucket endpoint, {region} are inserted at runtime
   * - cdn_url
     - https://{bucket}.{region}.cdn.digitaloceanspaces.com/{key}
     - S3 CDN url, {bucket}, {region} and {key} are inserted at runtime
   * - private
     - False
     - if true S3 files will not be readable online

Storage
-------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - path_generator
     - url
     - how to store the file in terms of directory structure: 'flat' sets to root; 'url' creates a directory based on the provided URL; 'random' creates a random directory.
   * - filename_generator
     - random
     - how to name stored files: 'random' creates a random string; 'static' uses a replicable strategy such as a hash.

Gsheets
-------

The following table lists all configuration options for this component:

.. list-table:: Configuration Options
   :header-rows: 1
   :widths: 25 20 55

   * - **Key**
     - **Default**
     - **Description**
   * - sheet
     - None
     - name of the sheet to archive
   * - sheet_id
     - None
     - (alternative to sheet name) the id of the sheet to archive
   * - header
     - 1
     - index of the header row (starts at 1)
   * - service_account
     - secrets/service_account.json
     - service account JSON file path
   * - columns
     - {'url': 'link', 'status': 'archive status', 'folder': 'destination folder', 'archive': 'archive location', 'date': 'archive date', 'thumbnail': 'thumbnail', 'timestamp': 'upload timestamp', 'title': 'upload title', 'text': 'text content', 'screenshot': 'screenshot', 'hash': 'hash', 'pdq_hash': 'perceptual hashes', 'wacz': 'wacz', 'replaywebpage': 'replaywebpage'}
     - names of columns in the google sheet (stringified JSON object)

