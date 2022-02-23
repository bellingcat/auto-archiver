from dataclasses import dataclass
import youtube_dl
from bs4 import BeautifulSoup
import requests
import tiktok_downloader
from loguru import logger
import os
import datetime
import ffmpeg
from botocore.errorfactory import ClientError
import time
import traceback

# TODO There should be a better way of generating keys, that adds the following info:
#           - name of sheet that it is being archived from
#             (this means we might archive the same media twice on different sheets, but that's OK I think)
#           - name of archiver/platform that the video comes from
#       This should make it easier to maintain and clean the archive later

# TODO "check_if_exists" has lots of repeated code across the archivers. Can this be
#      cleaned up? Difficult is we don't know the filename until the archivers start working.


def get_cdn_url(key):
    return 'https://{}.{}.cdn.digitaloceanspaces.com/{}'.format(
        os.getenv('DO_BUCKET'), os.getenv('DO_SPACES_REGION'), key)


def do_s3_upload(s3_client, f, key):
    s3_client.upload_fileobj(f, Bucket=os.getenv(
        'DO_BUCKET'), Key=key, ExtraArgs={'ACL': 'public-read'})


def get_key(filename):
    key = filename.split('/')[1]
    if 'unknown_video' in key:
        key = key.replace('unknown_video', 'jpg')
    return key


def get_thumbnails(filename, s3_client, duration=None):
    if not os.path.exists(filename.split('.')[0]):
        os.mkdir(filename.split('.')[0])

    fps = 0.5
    if duration is not None:
        duration = float(duration)

        if duration < 60:
            fps = 10.0 / duration
        elif duration < 120:
            fps = 20.0 / duration
        else:
            fps = 40.0 / duration

    stream = ffmpeg.input(filename)
    stream = ffmpeg.filter(stream, 'fps', fps=fps).filter('scale', 512, -1)
    stream.output(filename.split('.')[0] + '/out%d.jpg').run()

    thumbnails = os.listdir(filename.split('.')[0] + '/')
    cdn_urls = []

    for fname in thumbnails:
        if fname[-3:] == 'jpg':
            thumbnail_filename = filename.split('.')[0] + '/' + fname
            key = filename.split('/')[1].split('.')[0] + '/' + fname

            cdn_url = get_cdn_url(key)

            with open(thumbnail_filename, 'rb') as f:
                do_s3_upload(s3_client, f, key)

            cdn_urls.append(cdn_url)
            os.remove(thumbnail_filename)

    if len(cdn_urls) == 0:
        return ('None', 'None')

    key_thumb = cdn_urls[int(len(cdn_urls)*0.1)]

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

    thumb_index_cdn_url = get_cdn_url(thumb_index)

    return (key_thumb, thumb_index_cdn_url)


@dataclass
class ArchiveResult:
    status: str
    cdn_url: str = None
    thumbnail: str = None
    thumbnail_index: str = None
    duration: float = None
    title: str = None
    timestamp: datetime.datetime = None


class Archiver:
    def __init__(self, s3_client):
        self.s3 = s3_client

    def download(self, url):
        pass


class TelegramArchiver(Archiver):
    def download(self, url, check_if_exists=False):
        # detect URLs that we definitely cannot handle
        if 'http://t.me/' not in url and 'https://t.me/' not in url:
            return False

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'}
        status = "success"

        original_url = url

        if url[-8:] != "?embed=1":
            url += "?embed=1"

        t = requests.get(url, headers=headers)
        s = BeautifulSoup(t.content, 'html.parser')
        video = s.find("video")

        if video is None:
            return False  # could not find video

        video_url = video.get('src')
        key = video_url.split('/')[-1].split('?')[0]
        filename = 'tmp/' + key

        if check_if_exists:
            try:
                self.s3.head_object(Bucket=os.getenv('DO_BUCKET'), Key=key)

                # file exists
                cdn_url = get_cdn_url(key)

                status = 'already archived'

            except ClientError:
                pass

        v = requests.get(video_url, headers=headers)

        with open(filename, 'wb') as f:
            f.write(v.content)

        if status != 'already archived':
            cdn_url = get_cdn_url(key)

            with open(filename, 'rb') as f:
                do_s3_upload(self.s3, f, key)

        # extract duration from HTML
        duration = s.find_all('time')[0].contents[0]
        if ':' in duration:
            duration = float(duration.split(
                ':')[0])*60 + float(duration.split(':')[1])
        else:
            duration = float(duration)

        # process thumbnails
        key_thumb, thumb_index = get_thumbnails(
            filename, self.s3, duration=duration)
        os.remove(filename)

        return ArchiveResult(status=status, cdn_url=cdn_url, thumbnail=key_thumb, thumbnail_index=thumb_index,
                             duration=duration, title=original_url, timestamp=s.find_all('time')[1].get('datetime'))


class YoutubeDLArchiver(Archiver):
    def download(self, url, check_if_exists=False):
        ydl_opts = {'outtmpl': 'tmp/%(id)s.%(ext)s', 'quiet': False}
        if (url[0:21] == 'https://facebook.com/' or url[0:25] == 'https://wwww.facebook.com/') and os.getenv('FB_COOKIE'):
            logger.info('Using Facebook cookie')
            youtube_dl.utils.std_headers['cookie'] = os.getenv('FB_COOKIE')

        ydl = youtube_dl.YoutubeDL(ydl_opts)
        cdn_url = None
        status = 'success'

        try:
            info = ydl.extract_info(url, download=False)
        except youtube_dl.utils.DownloadError:
            # no video here
            return False

        if 'is_live' in info and info['is_live']:
            logger.warning("Live streaming media, not archiving now")
            return ArchiveResult(status="Streaming media")

        if check_if_exists:
            if 'entries' in info:
                if len(info['entries']) > 1:
                    logger.warning(
                        'YoutubeDLArchiver succeeded but cannot archive channels or pages with multiple videos')
                    return False
                elif len(info['entries']) == 0:
                    logger.warning(
                        'YoutubeDLArchiver succeeded but did not find video')
                    return False

                filename = ydl.prepare_filename(info['entries'][0])
            else:
                filename = ydl.prepare_filename(info)

            key = get_key(filename)

            try:
                self.s3.head_object(Bucket=os.getenv('DO_BUCKET'), Key=key)

                # file exists
                cdn_url = get_cdn_url(key)

                status = 'already archived'

            except ClientError:
                pass

        # sometimes this results in a different filename, so do this again
        info = ydl.extract_info(url, download=True)

        if 'entries' in info:
            if len(info['entries']) > 1:
                logger.warning(
                    'YoutubeDLArchiver cannot archive channels or pages with multiple videos')
                return False
            else:
                info = info['entries'][0]

        filename = ydl.prepare_filename(info)

        if not os.path.exists(filename):
            filename = filename.split('.')[0] + '.mkv'

        if status != 'already archived':
            key = get_key(filename)
            cdn_url = get_cdn_url(key)

            with open(filename, 'rb') as f:
                do_s3_upload(self.s3, f, key)

        # get duration
        duration = info['duration'] if 'duration' in info else None

        # get thumbnails
        try:
            key_thumb, thumb_index = get_thumbnails(
                filename, self.s3, duration=duration)
        except:
            key_thumb = ''
            thumb_index = 'Could not generate thumbnails'

        os.remove(filename)

        timestamp = info['timestamp'] if 'timestamp' in info else datetime.datetime.strptime(
            info['upload_date'], '%Y%m%d').timestamp() if 'upload_date' in info and info['upload_date'] is not None else None

        return ArchiveResult(status=status, cdn_url=cdn_url, thumbnail=key_thumb, thumbnail_index=thumb_index, duration=duration,
                             title=info['title'] if 'title' in info else None,
                             timestamp=timestamp)


class WaybackArchiver(Archiver):
    def __init__(self, s3_client):
        self.s3 = s3_client
        self.seen_urls = {}

    def download(self, url, check_if_exists=False):
        if check_if_exists and url in self.seen_urls:
            return self.seen_urls[url]

        ia_headers = {
            "Accept": "application/json",
            "Authorization": "LOW " + os.getenv('INTERNET_ARCHIVE_S3_KEY') + ":" + os.getenv('INTERNET_ARCHIVE_S3_SECRET')
        }

        r = requests.post(
            'https://web.archive.org/save/', headers=ia_headers, data={'url': url})

        if r.status_code != 200:
            return ArchiveResult(status="Internet archive failed")

        if 'job_id' not in r.json() and 'message' in r.json():
            return ArchiveResult(status=f"Internet archive failed: {r.json()['message']}")

        job_id = r.json()['job_id']

        status_r = requests.get(
            'https://web.archive.org/save/status/' + job_id, headers=ia_headers)

        retries = 0

        # wait 90-120 seconds for the archive job to finish
        while (status_r.status_code != 200 or status_r.json()['status'] == 'pending') and retries < 30:
            time.sleep(3)

            try:
                status_r = requests.get(
                    'https://web.archive.org/save/status/' + job_id, headers=ia_headers)
            except:
                time.sleep(1)

            retries += 1

        if status_r.status_code != 200:
            return ArchiveResult(status="Internet archive failed")

        status_json = status_r.json()

        if status_json['status'] != 'success':
            return ArchiveResult(status='Internet Archive failed: ' + str(status_json))

        archive_url = 'https://web.archive.org/web/' + \
            status_json['timestamp'] + '/' + status_json['original_url']

        try:
            r = requests.get(archive_url)

            parsed = BeautifulSoup(
                r.content, 'html.parser')

            title = parsed.find_all('title')[
                0].text

            if title == 'Wayback Machine':
                title = 'Could not get title'
        except:
            title = "Could not get title"

        result = ArchiveResult(
            status='Internet Archive fallback', cdn_url=archive_url, title=title)
        self.seen_urls[url] = result
        return result


class TiktokArchiver(Archiver):
    def download(self, url, check_if_exists=False):
        if 'tiktok.com' not in url:
            return False

        status = 'success'

        try:
            info = tiktok_downloader.info_post(url)
            key = 'tiktok_' + str(info.id) + '.mp4'
            cdn_url = get_cdn_url(key)
            filename = 'tmp/' + key

            if check_if_exists:
                try:
                    self.s3.head_object(Bucket=os.getenv('DO_BUCKET'), Key=key)

                    # file exists
                    cdn_url = get_cdn_url(key)

                    status = 'already archived'

                except ClientError:
                    pass

            media = tiktok_downloader.snaptik(url).get_media()

            if len(media) <= 0:
                if status == 'already archived':
                    return ArchiveResult(status='Could not download media, but already archived', cdn_url=cdn_url)
                else:
                    return ArchiveResult(status='Could not download media')

            media[0].download(filename)

            if status != 'already archived':
                with open(filename, 'rb') as f:
                    do_s3_upload(self.s3, f, key)

            try:
                key_thumb, thumb_index = get_thumbnails(
                    filename, self.s3, duration=info.duration)
            except:
                key_thumb = ''
                thumb_index = 'error creating thumbnails'

            os.remove(filename)

            return ArchiveResult(status=status, cdn_url=cdn_url, thumbnail=key_thumb,
                                 thumbnail_index=thumb_index, duration=info.duration, title=info.caption, timestamp=info.create.isoformat())

        except tiktok_downloader.Except.InvalidUrl:
            status = 'Invalid URL'
            return ArchiveResult(status=status)

        except:
            error = traceback.format_exc()
            status = 'Other Tiktok error: ' + str(error)
            return ArchiveResult(status=status)
