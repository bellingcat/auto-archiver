import os
import datetime
import argparse
import string
import requests
import shutil
import gspread
from loguru import logger
from dotenv import load_dotenv
from selenium import webdriver
import traceback

import archivers
from storages import S3Storage, S3Config
from storages.gd_storage import GDConfig, GDStorage
from utils import GWorksheet, mkdir_if_not_exists

import sys

# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
# from googleapiclient.http import MediaFileUpload
# from google.oauth2 import service_account

logger.add("logs/1trace.log", level="TRACE")
logger.add("logs/2info.log", level="INFO")
logger.add("logs/3success.log", level="SUCCESS")
logger.add("logs/4warning.log", level="WARNING")
logger.add("logs/5error.log", level="ERROR")

load_dotenv()

def update_sheet(gw, row, result: archivers.ArchiveResult):
    cell_updates = []
    row_values = gw.get_row(row)

    def batch_if_valid(col, val, final_value=None):
        final_value = final_value or val
        if val and gw.col_exists(col) and gw.get_cell(row_values, col) == '':
            cell_updates.append((row, col, final_value))

    cell_updates.append((row, 'status', result.status))

    batch_if_valid('archive', result.cdn_url)
    batch_if_valid('date', True, datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat())
    batch_if_valid('thumbnail', result.thumbnail,
                   f'=IMAGE("{result.thumbnail}")')
    batch_if_valid('thumbnail_index', result.thumbnail_index)
    batch_if_valid('title', result.title)
    batch_if_valid('duration', result.duration, str(result.duration))
    batch_if_valid('screenshot', result.screenshot)
    batch_if_valid('hash', result.hash)

    if result.timestamp is not None:
        if type(result.timestamp) == int:
            timestamp_string = datetime.datetime.fromtimestamp(result.timestamp).replace(tzinfo=datetime.timezone.utc).isoformat()
        elif type(result.timestamp) == str:
            timestamp_string = result.timestamp
        else:
            timestamp_string = result.timestamp.isoformat()

        batch_if_valid('timestamp', timestamp_string)

    gw.batch_set_cell(cell_updates)


def expand_url(url):
    # expand short URL links
    if 'https://t.co/' in url:
        try:
            r = requests.get(url)
            url = r.url
        except:
            logger.error(f'Failed to expand url {url}')
    return url


def process_sheet(sheet, usefilenumber, storage, header=1, columns=GWorksheet.COLUMN_NAMES):
    gc = gspread.service_account(filename='service_account.json')
    sh = gc.open(sheet)

    s3_config = S3Config(
        bucket=os.getenv('DO_BUCKET'),
        region=os.getenv('DO_SPACES_REGION'),
        key=os.getenv('DO_SPACES_KEY'),
        secret=os.getenv('DO_SPACES_SECRET')
    )

    gd_config = GDConfig(
        root_folder_id=os.getenv('GD_ROOT_FOLDER_ID'),
        # todo delete below
        bucket=os.getenv('DO_BUCKET'),
        region=os.getenv('DO_SPACES_REGION'),
        key=os.getenv('DO_SPACES_KEY'),
        secret=os.getenv('DO_SPACES_SECRET')
    )
   
    telegram_config = archivers.TelegramConfig(
        api_id=os.getenv('TELEGRAM_API_ID'),
        api_hash=os.getenv('TELEGRAM_API_HASH')
    )

    # loop through worksheets to check
    for ii, wks in enumerate(sh.worksheets()):
        logger.info(f'Opening worksheet ii={ii}: {wks.title} header={header}')
        gw = GWorksheet(wks, header_row=header, columns=columns)

        if not gw.col_exists('url'):
            logger.warning(
                f'No "{columns["url"]}" column found, skipping worksheet {wks.title}')
            continue

        if not gw.col_exists('status'):
            logger.warning(
                f'No "{columns["status"]}" column found, skipping worksheet {wks.title}')
            continue

        # archives will be in a folder 'doc_name/worksheet_name'
        s3_config.folder = f'{sheet.replace(" ", "_")}/{wks.title.replace(" ", "_")}/'
        s3_client = S3Storage(s3_config)

        gd_config.folder = f'{sheet.replace(" ", "_")}/{wks.title.replace(" ", "_")}/'
        gd_client = GDStorage(gd_config)

        # loop through rows in worksheet
        for row in range(1 + header, gw.count_rows() + 1):
            url = gw.get_cell(row, 'url')
            original_status = gw.get_cell(row, 'status')
            status = gw.get_cell(row, 'status', fresh=original_status in ['', None] and url != '')
            # logger.trace(f'Row {row} status {status}')
            if url != '' and status in ['', None]:
                gw.set_cell(row, 'status', 'Archive in progress')

                url = expand_url(url)

                # DM Feature flag
                if usefilenumber:
                    filenumber = gw.get_cell(row, 'filenumber')
                    logger.debug(f'filenumber is {filenumber}')
                    if filenumber == "":
                        logger.warning(f'Logic error on row {row} with url {url} - the feature flag for usefilenumber is True, yet cant find a corresponding filenumber')
                        gw.set_cell(row, 'status', 'Missing filenumber')
                        continue
                else:
                    # We will use this through the app to differentiate between where to save
                    filenumber = None

                # DM make a new driver every row so idempotent
                # otherwise cookies will be remembered
                options = webdriver.FirefoxOptions()
                options.headless = True
                options.set_preference('network.protocol-handler.external.tg', False)
                driver = webdriver.Firefox(options=options)
                driver.set_window_size(1400, 2000)
                # DM put in for telegram screenshots which don't come back
                driver.set_page_load_timeout(120)
        
                # client
                storage_client = None
                if storage == "s3":
                    storage_client = s3_client
                elif storage == "gd":
                    storage_client = gd_client
                else:
                    raise ValueError(f'Cant get storage_client {storage_client}')

                # order matters, first to succeed excludes remaining
                active_archivers = [
                    archivers.TelethonArchiver(storage_client, driver, telegram_config),
                    archivers.TelegramArchiver(storage_client, driver),
                    archivers.TiktokArchiver(storage_client, driver),
                    archivers.YoutubeDLArchiver(storage_client, driver, os.getenv('FACEBOOK_COOKIE')),
                    archivers.TwitterArchiver(storage_client, driver),
                    archivers.WaybackArchiver(storage_client, driver)
                ]
                for archiver in active_archivers:
                    logger.debug(f'Trying {archiver} on row {row}')

                    try:
                        # DM 
                        if usefilenumber:
                            # using filenumber to store in folders so can't check for existance of that url
                            result = archiver.download(url, check_if_exists=False, filenumber=filenumber)
                        else:
                            result = archiver.download(url, check_if_exists=True)

                    except Exception as e:
                        result = False
                        logger.error(f'Got unexpected error in row {row} with archiver {archiver} for url {url}: {e}\n{traceback.format_exc()}')

                    if result:
                        # DM add IA as this is a success really 
                        if result.status in ['success', 'already archived', 'Internet Archive fallback']:
                            result.status = archiver.name + \
                                ": " + str(result.status)
                            logger.success(
                                f'{archiver} succeeded on row {row}, url {url}')
                            break

                        # DM wayback has seen this url before so keep existing status
                        # if result.status == "wayback: Internet Archive fallback":
                        if "wayback: Internet Archive fallback" in result.status:
                            logger.success(
                                f'wayback has seen this url before so keep existing status on row {row}')
                            result.status = result.status.replace(' (duplicate)', '')
                            result.status = str(result.status) + " (duplicate)"
                            break

                        logger.warning(
                            f'{archiver} did not succeed on row {row}, url: {url}, final status: {result.status}')
                        result.status = archiver.name + \
                            ": " + str(result.status)
                # get rid of driver so can reload on next row
                driver.quit()

                if result:
                    update_sheet(gw, row, result)
                else:
                    gw.set_cell(row, 'status', 'failed: no archiver')
                    logger.success(f'Finshed worksheet {wks.title}')

@logger.catch
def main():
    # DM don't want to use print anymore
    # print(sys.argv[1:])
    logger.debug(f'Passed args:{sys.argv}')

    parser = argparse.ArgumentParser(
        description='Automatically archive social media videos from a Google Sheets document')
    parser.add_argument('--sheet', action='store', dest='sheet', help='the name of the google sheets document', required=True)
    parser.add_argument('--header', action='store', dest='header', default=1, type=int, help='1-based index for the header row')
    parser.add_argument('--private', action='store_true', help='Store content without public access permission')
    parser.add_argument('--use-filenumber-as-directory', action=argparse.BooleanOptionalAction, dest='usefilenumber',  \
         help='Will save files into a subfolder on cloud storage which has the File Number eg SM3012')
    parser.add_argument('--storage', action='store', dest='storage', default='s3', \
         help='s3 or gd storage. Default is s3. NOTE GD storage supports only using filenumber')

    for k, v in GWorksheet.COLUMN_NAMES.items():
        parser.add_argument(f'--col-{k}', action='store', dest=k, default=v, help=f'the name of the column to fill with {k} (defaults={v})')

    args = parser.parse_args()
    config_columns = {k: getattr(args, k).lower() for k in GWorksheet.COLUMN_NAMES.keys()}

    logger.info(f'Opening document {args.sheet} for header {args.header} using filenumber: {args.usefilenumber} and storage {args.storage}')

    # https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
    # filenumber is True (of type bool) when set or None when argument is not there
    # explicitly setting usefilenumber to a bool
    usefilenumber = False
    if args.usefilenumber:
        usefilenumber = True

    mkdir_if_not_exists('tmp')
    # DM added usefilenumber (default is False) and storage (default is s3) or gd (Google Drive)
    process_sheet(args.sheet, usefilenumber=usefilenumber, storage=args.storage, header=args.header, columns=config_columns)
    shutil.rmtree('tmp')


if __name__ == '__main__':
    main()
