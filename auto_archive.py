import os
import datetime
import argparse
import requests
import shutil
import gspread
from loguru import logger
from dotenv import load_dotenv
from selenium import webdriver
import traceback

import archivers
from storages import S3Storage, S3Config
from utils import GWorksheet, mkdir_if_not_exists
import sys

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


def process_sheet(sheet, header=1, columns=GWorksheet.COLUMN_NAMES):
    gc = gspread.service_account(filename='service_account.json')
    sh = gc.open(sheet)

    s3_config = S3Config(
        bucket=os.getenv('DO_BUCKET'),
        region=os.getenv('DO_SPACES_REGION'),
        key=os.getenv('DO_SPACES_KEY'),
        secret=os.getenv('DO_SPACES_SECRET')
    )
    telegram_config = archivers.TelegramConfig(
        api_id=os.getenv('TELEGRAM_API_ID'),
        api_hash=os.getenv('TELEGRAM_API_HASH')
    )

    options = webdriver.FirefoxOptions()
    options.headless = True
    options.set_preference('network.protocol-handler.external.tg', False)

    driver = webdriver.Firefox(options=options)
    driver.set_window_size(1400, 2000)
    driver.set_page_load_timeout(10)

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

        # order matters, first to succeed excludes remaining
        active_archivers = [
            archivers.TelethonArchiver(s3_client, driver, telegram_config),
            archivers.TelegramArchiver(s3_client, driver),
            archivers.TiktokArchiver(s3_client, driver),
            archivers.YoutubeDLArchiver(s3_client, driver),
            archivers.TwitterArchiver(s3_client, driver),
            archivers.WaybackArchiver(s3_client, driver)
        ]

        # loop through rows in worksheet
        for row in range(1 + header, gw.count_rows() + 1):
            url = gw.get_cell(row, 'url')
            original_status = gw.get_cell(row, 'status')
            status = gw.get_cell(row, 'status', fresh=original_status in ['', None] and url != '')
            if url != '' and status in ['', None]:
                gw.set_cell(row, 'status', 'Archive in progress')

                url = expand_url(url)

                for archiver in active_archivers:
                    logger.debug(f'Trying {archiver} on row {row}')

                    try:
                        result = archiver.download(url, check_if_exists=True)
                    except Exception as e:
                        result = False
                        logger.error(f'Got unexpected error in row {row} with archiver {archiver} for url {url}: {e}\n{traceback.format_exc()}')

                    if result:
                        if result.status in ['success', 'already archived']:
                            result.status = archiver.name + \
                                ": " + str(result.status)
                            logger.success(
                                f'{archiver} succeeded on row {row}')
                            break
                        logger.warning(
                            f'{archiver} did not succeed on row {row}, final status: {result.status}')
                        result.status = archiver.name + \
                            ": " + str(result.status)

                if result:
                    update_sheet(gw, row, result)
                else:
                    gw.set_cell(row, 'status', 'failed: no archiver')
        logger.success(f'Finshed worksheet {wks.title}')
    driver.quit()

@logger.catch
def main():
    logger.debug(f'Passed args:{sys.argv}')
    parser = argparse.ArgumentParser(
        description='Automatically archive social media videos from a Google Sheets document')
    parser.add_argument('--sheet', action='store', dest='sheet', help='the name of the google sheets document', required=True)
    parser.add_argument('--header', action='store', dest='header', default=1, type=int, help='1-based index for the header row')
    parser.add_argument('--private', action='store_true', help='Store content without public access permission')

    for k, v in GWorksheet.COLUMN_NAMES.items():
        parser.add_argument(f'--col-{k}', action='store', dest=k, default=v, help=f'the name of the column to fill with {k} (defaults={v})')

    args = parser.parse_args()
    config_columns = {k: getattr(args, k).lower() for k in GWorksheet.COLUMN_NAMES.keys()}

    logger.info(f'Opening document {args.sheet} for header {args.header}')

    mkdir_if_not_exists('tmp')
    process_sheet(args.sheet, header=args.header, columns=config_columns)
    shutil.rmtree('tmp')


if __name__ == '__main__':
    main()
