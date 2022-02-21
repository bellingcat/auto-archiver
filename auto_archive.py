import os
import datetime
import argparse
import math
import gspread
import boto3
from loguru import logger
from dotenv import load_dotenv

import archivers

load_dotenv()


def col_to_index(col):
    col = list(col)
    ndigits = len(col)
    alphabet = ' ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    v = 0
    i = ndigits - 1

    for digit in col:
        index = alphabet.find(digit)
        v += (26 ** i) * index
        i -= 1

    return v - 1


def index_to_col(index):
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    if index > 25:
        t = index
        dig = 0
        while t > 25:
            t = math.floor(t / 26)
            dig += 1
        return alphabet[t - 1] + index_to_col(index - t * int(math.pow(26, dig)))
    else:
        return alphabet[index]


def update_sheet(wks, row, result : archivers.ArchiveResult, columns, v):
    update = []

    if columns['status'] is not None:
        update += [{
            'range': columns['status'] + str(row),
            'values': [[result.status]]
        }]

    if result.cdn_url and columns['archive'] is not None and v[col_to_index(columns['archive'])] == '':
        update += [{
            'range': columns['archive'] + str(row),
            'values': [[result.cdn_url]]
        }]

    if columns['date'] is not None and v[col_to_index(columns['date'])] == '':
        update += [{
            'range': columns['date'] + str(row),
            'values': [[datetime.datetime.now().isoformat()]]
        }]

    if result.thumbnail and columns['thumbnail'] is not None and v[col_to_index(columns['thumbnail'])] == '':
        update += [{
            'range': columns['thumbnail'] + str(row),
            'values': [['=IMAGE("' + result.thumbnail + '")']]
        }]

    if result.thumbnail_index and columns['thumbnail_index'] is not None and v[col_to_index(columns['thumbnail_index'])] == '':
        update += [{
            'range': columns['thumbnail_index'] + str(row),
            'values': [[result.thumbnail_index]]
        }]

    if result.timestamp and columns['timestamp'] is not None and v[col_to_index(columns['timestamp'])] == '':
        update += [{
            'range': columns['timestamp'] + str(row),
            'values': [[result.timestamp]] if type(result.timestamp) == str else [[datetime.datetime.fromtimestamp(result.timestamp).isoformat()]]
        }]

    if result.title and columns['title'] is not None and v[col_to_index(columns['title'])] == '':
        update += [{
            'range': columns['title'] + str(row),
            'values': [[result.title]]
        }]

    if result.duration and columns['duration'] is not None and v[col_to_index(columns['duration'])] == '':
        update += [{
            'range': columns['duration'] + str(row),
            'values': [[str(result.duration)]]
        }]

    wks.batch_update(update, value_input_option='USER_ENTERED')


# def record_stream(url, s3_client, wks, i, columns, v):
#     video_data, status = download_vid(url, s3_client)
#     update_sheet(wks, i, status, video_data, columns, v)


def process_sheet(sheet):
    gc = gspread.service_account(filename='service_account.json')
    sh = gc.open(sheet)
    n_worksheets = len(sh.worksheets())

    s3_client = boto3.client('s3',
                             region_name=os.getenv('DO_SPACES_REGION'),
                             endpoint_url='https://{}.digitaloceanspaces.com'.format(
                                 os.getenv('DO_SPACES_REGION')),
                             aws_access_key_id=os.getenv('DO_SPACES_KEY'),
                             aws_secret_access_key=os.getenv('DO_SPACES_SECRET'))

    # loop through worksheets to check
    for ii in range(n_worksheets):
        logger.info("Opening worksheet " + str(ii))
        wks = sh.get_worksheet(ii)
        values = wks.get_all_values()

        headers = [v.lower() for v in values[0]]
        columns = {}

        columns['url'] = index_to_col(headers.index(
            'media url')) if 'media url' in headers else index_to_col(headers.index(
                'source url')) if 'source url' in headers else None

        if columns['url'] is None:
            logger.warning("No 'Media URL' column found, skipping")
            continue

        url_index = col_to_index(columns['url'])

        columns['archive'] = index_to_col(headers.index(
            'archive location')) if 'archive location' in headers else None
        columns['date'] = index_to_col(headers.index(
            'archive date')) if 'archive date' in headers else None
        columns['status'] = index_to_col(headers.index(
            'archive status')) if 'archive status' in headers else None

        if columns['status'] is None:
            logger.warning("No 'Archive status' column found, skipping")
            continue

        columns['thumbnail'] = index_to_col(headers.index(
            'thumbnail')) if 'thumbnail' in headers else None
        columns['thumbnail_index'] = index_to_col(headers.index(
            'thumbnail index')) if 'thumbnail index' in headers else None
        columns['timestamp'] = index_to_col(headers.index(
            'upload timestamp')) if 'upload timestamp' in headers else None
        columns['title'] = index_to_col(headers.index(
            'upload title')) if 'upload title' in headers else None
        columns['duration'] = index_to_col(headers.index(
            'duration')) if 'duration' in headers else None


        # order matters, first to succeed excludes remaining
        active_archivers = [
            archivers.TelegramArchiver(s3_client),
            archivers.TiktokArchiver(s3_client),
            archivers.YoutubeDLArchiver(s3_client),
            archivers.WaybackArchiver(s3_client)
        ]


        # loop through rows in worksheet
        for i in range(2, len(values)+1):
            v = values[i-1]

            if v[url_index] != "" and v[col_to_index(columns['status'])] == "":
                latest_val = wks.acell(
                    columns['status'] + str(i)).value

                # check so we don't step on each others' toes
                if latest_val == '' or latest_val is None:
                    wks.update(
                        columns['status'] + str(i), 'Archive in progress')

                    for archiver in active_archivers:
                        logger.debug(f"Trying {archiver} on row {i}")
                        result = archiver.download(v[url_index], check_if_exists=True)
                        if result:
                            logger.info(f"{archiver} succeeded on row {i}")
                            break

                    if result:
                        update_sheet(wks, i, result, columns, v)


                        # except:
                            # if any unexpected errors occured, log these into the Google Sheet
                            # t, value, traceback = sys.exc_info()

                            # update_sheet(wks, i, str(
                            #     value), {}, columns, v)


def main():
    parser = argparse.ArgumentParser(
        description="Automatically archive social media videos from a Google Sheet")
    parser.add_argument("--sheet", action="store", dest="sheet")
    args = parser.parse_args()

    logger.info("Opening document " + args.sheet)

    process_sheet(args.sheet)


if __name__ == "__main__":
    main()
