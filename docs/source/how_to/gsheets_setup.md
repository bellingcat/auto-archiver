# Using Google Sheets

The `--gsheet_feeder.sheet` property is the name of the Google Sheet to check for URLs. 
This sheet must have been shared with the Google Service account used by `gspread`. 
This sheet must also have specific columns (case-insensitive) in the `header` - see the [Gsheet Feeder Docs](modules/autogen/feeder/gsheet_feeder.md) for more info. The default names of these columns and their purpose is:

Inputs:

* **Link** *(required)*: the URL of the post to archive
* **Destination folder**: custom folder for archived file (regardless of storage)

Outputs:
* **Archive status** *(required)*: Status of archive operation
* **Archive location**: URL of archived post
* **Archive date**: Date archived
* **Thumbnail**: Embeds a thumbnail for the post in the spreadsheet
* **Timestamp**: Timestamp of original post
* **Title**: Post title
* **Text**: Post text
* **Screenshot**: Link to screenshot of post
* **Hash**: Hash of archived HTML file (which contains hashes of post media) - for checksums/verification
* **Perceptual Hash**: Perceptual hashes of found images - these can be used for de-duplication of content
* **WACZ**: Link to a WACZ web archive of post
* **ReplayWebpage**: Link to a ReplayWebpage viewer of the WACZ archive

For example, this is a spreadsheet configured with all of the columns for the auto archiver and a few URLs to archive. (Note that the column names are not case sensitive.)

![A screenshot of a Google Spreadsheet with column headers defined as above, and several Youtube and Twitter URLs in the "Link" column](../demo-before.png)

Now the auto archiver can be invoked, with this command in this example: `docker run --rm -v $PWD/secrets:/app/secrets -v $PWD/local_archive:/app/local_archive bellingcat/auto-archiver:dockerize --config secrets/orchestration-global.yaml --gsheet_feeder.sheet "Auto archive test 2023-2"`. Note that the sheet name has been overridden/specified in the command line invocation.

When the auto archiver starts running, it updates the "Archive status" column.

![A screenshot of a Google Spreadsheet with column headers defined as above, and several Youtube and Twitter URLs in the "Link" column. The auto archiver has added "archive in progress" to one of the status columns.](../demo-progress.png)

The links are downloaded and archived, and the spreadsheet is updated to the following:

![A screenshot of a Google Spreadsheet with videos archived and metadata added per the description of the columns above.](../demo-after.png)

Note that the first row is skipped, as it is assumed to be a header row (`--gsheet_feeder.header=1` and you can change it if you use more rows above). Rows with an empty URL column, or a non-empty archive column are also skipped. All sheets in the document will be checked.

The "archive location" link contains the path of the archived file, in local storage, S3, or in Google Drive.

![The archive result for a link in the demo sheet.](../demo-archive.png)
