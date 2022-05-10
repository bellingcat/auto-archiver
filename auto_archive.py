# import os
import datetime
# import argparse
import shutil
# import gspread
from loguru import logger
from dotenv import load_dotenv

import traceback

# import archivers
from archivers import TelethonArchiver, TelegramArchiver, TiktokArchiver, YoutubeDLArchiver, TwitterArchiver, WaybackArchiver, ArchiveResult
from utils import GWorksheet, mkdir_if_not_exists, expand_url
from configs import Config

load_dotenv()


def update_sheet(gw, row, result: ArchiveResult):
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


def process_sheet(c: Config, sheet, header=1, columns=GWorksheet.COLUMN_NAMES):
    sh = c.gsheets_client.open(sheet)

    # loop through worksheets to check
    for ii, wks in enumerate(sh.worksheets()):
        logger.info(f'Opening worksheet {ii}: "{wks.title}" header={c.header}')
        gw = GWorksheet(wks, header_row=c.header, columns=c.column_names)

        if not gw.col_exists('url'):
            logger.warning(
                f'No "{c.column_names["url"]}" column found, skipping worksheet {wks.title}')
            continue

        if not gw.col_exists('status'):
            logger.warning(
                f'No "{c.column_names["status"]}" column found, skipping worksheet {wks.title}')
            continue

        # archives will be in a folder 'doc_name/worksheet_name'
        c.set_folder(f'{sheet.replace(" ", "_")}/{wks.title.replace(" ", "_")}/')
        storage = c.get_storage()

        # order matters, first to succeed excludes remaining
        active_archivers = [
            TelethonArchiver(storage, c.webdriver, c.telegram_config),
            TelegramArchiver(storage, c.webdriver),
            TiktokArchiver(storage, c.webdriver),
            YoutubeDLArchiver(storage, c.webdriver),
            TwitterArchiver(storage, c.webdriver),
            WaybackArchiver(storage, c.webdriver)
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


def main():
    c = Config()
    c.parse()

    logger.info(f'Opening document {c.sheet} for header {c.header}')

    mkdir_if_not_exists(c.tmp_folder)
    process_sheet(c, c.sheet, header=c.header, columns=c.column_names)
    shutil.rmtree(c.tmp_folder)
    c.webdriver.quit()


if __name__ == '__main__':
    main()
