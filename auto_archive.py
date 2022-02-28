import os
import datetime
import argparse
import requests
import shutil
import gspread
from loguru import logger
from dotenv import load_dotenv
from selenium import webdriver

import archivers
from storages import S3Storage, S3Config
from utils import GWorksheet, mkdir_if_not_exists

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


def process_sheet(sheet, header=1):
    gc = gspread.service_account(filename='service_account.json')
    sh = gc.open(sheet)

    s3_config = S3Config(
        bucket=os.getenv('DO_BUCKET'),
        region=os.getenv('DO_SPACES_REGION'),
        key=os.getenv('DO_SPACES_KEY'),
        secret=os.getenv('DO_SPACES_SECRET')
    )

    options = webdriver.FirefoxOptions()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    driver.set_window_size(1400, 2000)

    # loop through worksheets to check
    for ii, wks in enumerate(sh.worksheets()):
        logger.info(f'Opening worksheet {ii}: "{wks.title}"')
        gw = GWorksheet(wks, header_row=header)

        if not gw.col_exists('url'):
            logger.warning(
                f'No "Media URL" column found, skipping worksheet {wks.title}')
            continue

        if not gw.col_exists('status'):
            logger.warning(
                f'No "Archive status" column found, skipping worksheet {wks.title}')
            continue

        # archives will be in a folder 'doc_name/worksheet_name'
        s3_config.folder = f'{sheet.replace(" ", "_")}/{wks.title.replace(" ", "_")}/'
        s3_client = S3Storage(s3_config)

        # order matters, first to succeed excludes remaining
        active_archivers = [
            archivers.TelegramArchiver(s3_client, driver),
            archivers.TiktokArchiver(s3_client, driver),
            archivers.YoutubeDLArchiver(s3_client, driver),
            archivers.TwitterArchiver(s3_client, driver),
            archivers.WaybackArchiver(s3_client, driver)
        ]

        values = gw.get_values()
        # loop through rows in worksheet
        for row in range(1 + header, gw.count_rows() + 1):
            row_values = values[row-1]
            url = gw.get_cell(row_values, 'url')
            status = gw.get_cell(row_values, 'status')
            if url != '' and status in ['', None]:
                url = gw.get_cell(row, 'url')
                status = gw.get_cell(status, 'status')

                if url != '' and status in ['', None]:
                    gw.set_cell(row, 'status', 'Archive in progress')

                    url = expand_url(url)

                    for archiver in active_archivers:
                        logger.debug(f'Trying {archiver} on row {row}')

                        try:
                            result = archiver.download(url, check_if_exists=True)
                        except Exception as e:
                            result = False
                            logger.error(
                                f'Got unexpected error in row {row} with archiver {archiver} for url {url}: {e}')

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

    driver.quit()


def main():
    parser = argparse.ArgumentParser(
        description='Automatically archive social media videos from a Google Sheets document')
    parser.add_argument('--sheet', action='store', dest='sheet')
    parser.add_argument('--header', action='store', dest='header', default=1, type=int)
    args = parser.parse_args()

    logger.info(f'Opening document {args.sheet}')

    mkdir_if_not_exists('tmp')
    process_sheet(args.sheet, header=args.header)
    shutil.rmtree('tmp')


if __name__ == '__main__':
    main()
