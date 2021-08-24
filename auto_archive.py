import gspread
import youtube_dl
from pathlib import Path
import sys
import datetime
import boto3
import os
from dotenv import load_dotenv
from botocore.errorfactory import ClientError
import argparse
import math
import ffmpeg
import threading
import time
from bs4 import BeautifulSoup
import requests

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


def get_thumbnails(filename, s3_client):
    if not os.path.exists(filename.split('.')[0]):
        os.mkdir(filename.split('.')[0])

    stream = ffmpeg.input(filename)
    stream = ffmpeg.filter(stream, 'fps', fps=0.5).filter('scale', 512, -1)
    stream.output(filename.split('.')[0] + '/out%d.jpg').run()

    thumbnails = os.listdir(filename.split('.')[0] + '/')
    cdn_urls = []

    for fname in thumbnails:
        thumbnail_filename = filename.split('.')[0] + '/' + fname
        key = filename.split('/')[1].split('.')[0] + '/' + fname

        cdn_url = 'https://{}.{}.cdn.digitaloceanspaces.com/{}'.format(
            os.getenv('DO_BUCKET'), os.getenv('DO_SPACES_REGION'), key)

        with open(thumbnail_filename, 'rb') as f:
            s3_client.upload_fileobj(f, Bucket=os.getenv(
                'DO_BUCKET'), Key=key, ExtraArgs={'ACL': 'public-read'})

        cdn_urls.append(cdn_url)
        os.remove(thumbnail_filename)

    key_thumb = cdn_urls[int(len(cdn_urls)*0.25)]

    index_page = f'''<html><head><title>{filename}</title></head>
        <body>'''

    for t in cdn_urls:
        index_page += f'<img src="{t}" />'

    index_page += f"</body></html>"
    index_fname = filename.split('.')[0] + '/index.html'

    with open(index_fname, 'w') as f:
        f.write(index_page)

    thumb_index = filename.split('/')[1].split('.')[0] + '/index.html'

    s3_client.upload_fileobj(open(index_fname, 'rb'), Bucket=os.getenv(
        'DO_BUCKET'), Key=thumb_index, ExtraArgs={'ACL': 'public-read', 'ContentType': 'text/html'})

    thumb_index_cdn_url = 'https://{}.{}.cdn.digitaloceanspaces.com/{}'.format(
        os.getenv('DO_BUCKET'), os.getenv('DO_SPACES_REGION'), thumb_index)

    return (key_thumb, thumb_index_cdn_url)


def download_telegram_video(url, s3_client, check_if_exists=False):
    status = 'success'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'}

    original_url = url

    if url[-8:] != "?embed=1":
        url += "?embed=1"

    t = requests.get(url, headers=headers)
    s = BeautifulSoup(t.content, 'html.parser')
    video = s.find("video")

    if video is None:
        return ({}, 'No telegram video found')
    else:
        video_url = video.get('src')
        key = video_url.split('/')[-1].split('?')[0]
        filename = 'tmp/' + key
        print(video_url, key)

        if check_if_exists:
            try:
                s3_client.head_object(Bucket=os.getenv('DO_BUCKET'), Key=key)

                # file exists
                cdn_url = 'https://{}.{}.cdn.digitaloceanspaces.com/{}'.format(
                    os.getenv('DO_BUCKET'), os.getenv('DO_SPACES_REGION'), key)

                status = 'already archived'

            except ClientError:
                pass

        v = requests.get(video_url, headers=headers)

        with open(filename, 'wb') as f:
            f.write(v.content)

        if status != 'already archived':
            cdn_url = 'https://{}.{}.cdn.digitaloceanspaces.com/{}'.format(
                os.getenv('DO_BUCKET'), os.getenv('DO_SPACES_REGION'), key)

            with open(filename, 'rb') as f:
                s3_client.upload_fileobj(f, Bucket=os.getenv(
                    'DO_BUCKET'), Key=key, ExtraArgs={'ACL': 'public-read'})

        key_thumb, thumb_index = get_thumbnails(filename, s3_client)
        os.remove(filename)

        video_data = {
            'cdn_url': cdn_url,
            'thumbnail': key_thumb,
            'thumbnail_index': thumb_index,
            'duration': s.find_all('time')[0].contents[0],
            'title': original_url,
            'timestamp': s.find_all('time')[1].get('datetime')
        }

        return (video_data, status)


def internet_archive(url, s3_client):
    r = requests.post(
        'https://web.archive.org/save/', headers={
            "Accept": "application/json",
            "Authorization": "LOW " + os.getenv('INTERNET_ARCHIVE_S3_KEY') + ":" + os.getenv('INTERNET_ARCHIVE_S3_SECRET')
        }, data={'url': url})

    if r.status_code != 200:
        return ({}, 'Internet archive failed')
    else:
        job_id = r.json()['job_id']

        status_r = requests.get(
            'https://web.archive.org/save/status/' + job_id, headers={
                "Accept": "application/json",
                "Authorization": "LOW " + os.getenv('INTERNET_ARCHIVE_S3_KEY') + ":" + os.getenv('INTERNET_ARCHIVE_S3_SECRET')
            })

        retries = 0

        while status_r.json()['status'] == 'pending' and retries < 40:
            time.sleep(5)

            status_r = requests.get(
                'https://web.archive.org/save/status/' + job_id, headers={
                    "Accept": "application/json",
                    "Authorization": "LOW " + os.getenv('INTERNET_ARCHIVE_S3_KEY') + ":" + os.getenv('INTERNET_ARCHIVE_S3_SECRET')
                })

            retries += 1

        status_json = status_r.json()

        if status_json['status'] == 'success':
            url = 'https://web.archive.org/web/' + \
                status_json['timestamp'] + '/' + status_json['original_url']

            r = requests.get(url)

            parsed = BeautifulSoup(
                r.content, 'html.parser')
            title = parsed.find_all('title')[
                0].text

            return ({'cdn_url': url, 'title': title}, 'Internet Archive fallback')
        else:
            return ({}, 'Internet Archive failed: ' + status_json['message'])


def download_vid(url, s3_client, check_if_exists=False):
    ydl_opts = {'outtmpl': 'tmp/%(id)s.%(ext)s', 'quiet': False}
    if url[0:20] == 'https://facebook.com' and os.getenv('FB_COOKIE'):
        youtube_dl.utils.std_headers['cookie'] = os.getenv('FB_COOKIE')
    ydl = youtube_dl.YoutubeDL(ydl_opts)
    cdn_url = None
    status = 'success'

    if check_if_exists:
        info = ydl.extract_info(url, download=False)

        if 'entries' in info:
            if len(info['entries']) > 1:
                raise Exception(
                    'ERROR: Cannot archive channels or pages with multiple videos')

            filename = ydl.prepare_filename(info['entries'][0])
        else:
            filename = ydl.prepare_filename(info)

        key = filename.split('/')[1]

        try:
            s3_client.head_object(Bucket=os.getenv('DO_BUCKET'), Key=key)

            # file exists
            cdn_url = 'https://{}.{}.cdn.digitaloceanspaces.com/{}'.format(
                os.getenv('DO_BUCKET'), os.getenv('DO_SPACES_REGION'), key)

            status = 'already archived'

        except ClientError:
            pass

    # sometimes this results in a different filename, so do this again
    info = ydl.extract_info(url, download=True)

    if 'entries' in info:
        if len(info['entries']) > 1:
            raise Exception(
                'ERROR: Cannot archive channels or pages with multiple videos')

        filename = ydl.prepare_filename(info['entries'][0])
    else:
        filename = ydl.prepare_filename(info)

    if not os.path.exists(filename):
        filename = filename.split('.')[0] + '.mkv'

    if status != 'already archived':
        key = filename.split('/')[1]
        cdn_url = 'https://{}.{}.cdn.digitaloceanspaces.com/{}'.format(
            os.getenv('DO_BUCKET'), os.getenv('DO_SPACES_REGION'), key)

        with open(filename, 'rb') as f:
            s3_client.upload_fileobj(f, Bucket=os.getenv(
                'DO_BUCKET'), Key=key, ExtraArgs={'ACL': 'public-read'})

    key_thumb, thumb_index = get_thumbnails(filename, s3_client)
    os.remove(filename)

    video_data = {
        'cdn_url': cdn_url,
        'thumbnail': key_thumb,
        'thumbnail_index': thumb_index,
        'duration': info['duration'] if 'duration' in info else None,
        'title': info['title'] if 'title' in info else None,
        'timestamp': info['timestamp'] if 'timestamp' in info else datetime.datetime.strptime(info['upload_date'], '%Y%m%d').timestamp() if 'upload_date' in info else None,
    }

    return (video_data, status)


def update_sheet(wks, row, status, video_data, columns, v):
    update = []

    if columns['status'] is not None:
        update += [{
            'range': columns['status'] + str(row),
            'values': [[status]]
        }]

    if 'cdn_url' in video_data and video_data['cdn_url'] is not None and columns['archive'] is not None and v[col_to_index(columns['archive'])] == '':
        update += [{
            'range': columns['archive'] + str(row),
            'values': [[video_data['cdn_url']]]
        }]

    if 'date' in video_data and columns['date'] is not None and v[col_to_index(columns['date'])] == '':
        update += [{
            'range': columns['date'] + str(row),
            'values': [[datetime.datetime.now().isoformat()]]
        }]

    if 'thumbnail' in video_data and columns['thumbnail'] is not None and v[col_to_index(columns['thumbnail'])] == '':
        update += [{
            'range': columns['thumbnail'] + str(row),
            'values': [['=IMAGE("' + video_data['thumbnail'] + '")']]
        }]

    if 'thumbnail_index' in video_data and columns['thumbnail_index'] is not None and v[col_to_index(columns['thumbnail_index'])] == '':
        update += [{
            'range': columns['thumbnail_index'] + str(row),
            'values': [[video_data['thumbnail_index']]]
        }]

    if 'timestamp' in video_data and columns['timestamp'] is not None and video_data['timestamp'] is not None and v[col_to_index(columns['timestamp'])] == '':
        update += [{
            'range': columns['timestamp'] + str(row),
            'values': [[video_data['timestamp']]] if type(video_data['timestamp']) == str else [[datetime.datetime.fromtimestamp(video_data['timestamp']).isoformat()]]
        }]

    if 'title' in video_data and columns['title'] is not None and video_data['title'] is not None and v[col_to_index(columns['title'])] == '':
        update += [{
            'range': columns['title'] + str(row),
            'values': [[video_data['title']]]
        }]

    if 'duration' in video_data and columns['duration'] is not None and video_data['duration'] is not None and v[col_to_index(columns['duration'])] == '':
        update += [{
            'range': columns['duration'] + str(row),
            'values': [[str(video_data['duration'])]]
        }]

    wks.batch_update(update, value_input_option='USER_ENTERED')


def record_stream(url, s3_client, wks, i, columns, v):
    video_data, status = download_vid(url, s3_client)
    update_sheet(wks, i, status, video_data, columns, v)


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
        print("Opening worksheet " + str(ii))
        wks = sh.get_worksheet(ii)
        values = wks.get_all_values()

        headers = [v.lower() for v in values[0]]
        columns = {}

        columns['url'] = index_to_col(headers.index(
            'media url')) if 'media url' in headers else index_to_col(headers.index(
                'source url')) if 'source url' in headers else None

        if columns['url'] is None:
            print("No 'Media URL' column found, skipping")
            continue

        url_index = col_to_index(columns['url'])

        columns['archive'] = index_to_col(headers.index(
            'archive location')) if 'archive location' in headers else None
        columns['date'] = index_to_col(headers.index(
            'archive date')) if 'archive date' in headers else None
        columns['status'] = index_to_col(headers.index(
            'archive status')) if 'archive status' in headers else None

        if columns['status'] is None:
            print("No 'Archive status' column found, skipping")
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

        # loop through rows in worksheet
        for i in range(2, len(values)+1):
            v = values[i-1]

            if v[url_index] != "" and v[col_to_index(columns['status'])] == "":
                latest_val = wks.acell(
                    columns['status'] + str(i)).value

                # check so we don't step on each others' toes
                if latest_val == '' or latest_val is None:
                    if 'http://t.me/' in v[url_index] or 'https://t.me/' in v[url_index]:
                        wks.update(
                            columns['status'] + str(i), 'Archive in progress')

                        video_data, status = download_telegram_video(
                            v[url_index], s3_client, check_if_exists=True)
                        update_sheet(wks, i, status, video_data, columns, v)
                    else:
                        try:
                            ydl_opts = {
                                'outtmpl': 'tmp/%(id)s.%(ext)s', 'quiet': False}
                            ydl = youtube_dl.YoutubeDL(ydl_opts)
                            info = ydl.extract_info(
                                v[url_index], download=False)

                            if 'is_live' in info and info['is_live']:
                                wks.update(columns['status'] +
                                           str(i), 'Recording stream')
                                t = threading.Thread(target=record_stream, args=(
                                    v[url_index], s3_client, wks, i, columns, v))
                                t.start()
                                continue
                            elif 'is_live' not in info or not info['is_live']:
                                video_data, status = download_vid(
                                    v[url_index], s3_client, check_if_exists=True)
                                update_sheet(wks, i, status,
                                             video_data, columns, v)
                        except:
                            # i'm sure there's a better way to handle this than nested try/catch blocks
                            try:
                                wks.update(
                                    columns['status'] + str(i), 'Archive in progress')

                                print("Trying Internet Archive fallback")

                                video_data, status = internet_archive(
                                    v[url_index], s3_client)
                                update_sheet(wks, i, status,
                                             video_data, columns, v)

                            except:
                                # if any unexpected errors occured, log these into the Google Sheet
                                t, value, traceback = sys.exc_info()

                                update_sheet(wks, i, str(
                                    value), {}, columns, v)


def main():
    parser = argparse.ArgumentParser(
        description="Automatically use youtube-dl to download media from a Google Sheet")
    parser.add_argument("--sheet", action="store", dest="sheet")
    args = parser.parse_args()

    print("Opening document " + args.sheet)

    process_sheet(args.sheet)


if __name__ == "__main__":
    main()
