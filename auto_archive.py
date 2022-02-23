import os
import datetime
import argparse
import requests
import gspread
from loguru import logger
from dotenv import load_dotenv

import archivers
from storages import S3Storage, S3Config
from gworksheet import GWorksheet

load_dotenv()


def update_sheet(gw, row, result: archivers.ArchiveResult):
    update = []

    def batch_if_valid(col, val, final_value=None):
        final_value = final_value or val
        if val and gw.col_exists(col) and gw.cell(row, col) == '':
            update.append((row, col, final_value))

    update.append((row, 'status', result.status))

    batch_if_valid('archive', result.cdn_url)
    batch_if_valid('archive', True, datetime.datetime.now().isoformat())
    batch_if_valid('thumbnail', result.thumbnail, f'=IMAGE("{result.thumbnail}")')
    batch_if_valid('thumbnail_index', result.thumbnail_index)
    batch_if_valid('title', result.title)
    batch_if_valid('duration', result.duration, str(result.duration))

    if result.timestamp and type(result.timestamp) != str:
        result.timestamp = datetime.datetime.fromtimestamp(result.timestamp).isoformat()
    batch_if_valid('timestamp', result.timestamp)

    gw.update_batch(update)


def process_sheet(sheet):
    gc = gspread.service_account(filename='service_account.json')
    sh = gc.open(sheet)

    s3_config = S3Config(
        bucket=os.getenv('DO_BUCKET'),
        region=os.getenv('DO_SPACES_REGION'),
        key=os.getenv('DO_SPACES_KEY'),
        secret=os.getenv('DO_SPACES_SECRET')
    )

    # loop through worksheets to check
    for ii, wks in enumerate(sh.worksheets()):
        logger.info(f'Opening worksheet {ii}: "{wks.title}"')
        gw = GWorksheet(wks)

        if not gw.col_exists('url'):
            logger.warning(f'No "Media URL" column found, skipping worksheet {wks.title}')
            continue

        if not gw.col_exists('status'):
            logger.warning("No 'Archive status' column found, skipping")
            continue

        # archives will be in a folder 'doc_name/worksheet_name'
        s3_config.folder = f'{sheet}/{wks.title}/'
        s3_client = S3Storage(s3_config)

        # order matters, first to succeed excludes remaining
        active_archivers = [
            archivers.TelegramArchiver(s3_client),
            archivers.TiktokArchiver(s3_client),
            archivers.YoutubeDLArchiver(s3_client),
            archivers.WaybackArchiver(s3_client)
        ]

        # loop through rows in worksheet
        for i in range(2, gw.count_rows() + 1):
            row = gw.get_row(i)
            url = gw.cell(row, 'url')
            status = gw.cell(row, 'status')
            if url != '' and status in ['', None]:
                gw.update(i, 'status', 'Archive in progress')

                # expand short URL links
                if 'https://t.co/' in url:
                    r = requests.get(url)
                    url = r.url

                for archiver in active_archivers:
                    logger.debug(f'Trying {archiver} on row {i}')
                    result = archiver.download(url, check_if_exists=True)

                    if result:
                        logger.success(f'{archiver} succeeded on row {i}')
                        break

                if result:
                    update_sheet(gw, i, result)
                else:
                    gw.update(i, 'status', 'failed: no archiver')

        #             # except:
        #             # if any unexpected errors occured, log these into the Google Sheet
        #             # t, value, traceback = sys.exc_info()

        #             # update_sheet(wks, i, str(
        #             #     value), {}, columns, v)


def main():
    parser = argparse.ArgumentParser(
        description='Automatically archive social media videos from a Google Sheets document')
    parser.add_argument('--sheet', action='store', dest='sheet')
    args = parser.parse_args()

    logger.info(f'Opening document {args.sheet}')

    process_sheet(args.sheet)


if __name__ == '__main__':
    main()
