import gspread
import youtube_dl
from pathlib import Path
import sys
import datetime
import boto3
import os
from dotenv import load_dotenv
from botocore.errorfactory import ClientError

load_dotenv()

gc = gspread.service_account()
sh = gc.open("Bellingcat media archiver")
wks = sh.sheet1
values = wks.get_all_values()

ydl_opts = {'outtmpl': 'tmp/%(id)s.%(ext)s', 'quiet': False}
ydl = youtube_dl.YoutubeDL(ydl_opts)

s3_client = boto3.client('s3',
        region_name=os.getenv('DO_SPACES_REGION'),
        endpoint_url='https://{}.digitaloceanspaces.com'.format(os.getenv('DO_SPACES_REGION')),
        aws_access_key_id=os.getenv('DO_SPACES_KEY'),
        aws_secret_access_key=os.getenv('DO_SPACES_SECRET'))

for i in range(2, len(values)+1):
    v = values[i-1]

    if v[2] == "":
        print(v[0])

        try:
            info = ydl.extract_info(v[0], download=False)

            if 'entries' in info:
                if len(info['entries']) > 1:
                    raise Exception('ERROR: Cannot archive channels or pages with multiple videos')

                filename = ydl.prepare_filename(info['entries'][0])
            else:
                filename = ydl.prepare_filename(info)
            
            print(filename)
            key = filename.split('/')[1]
            cdn_url = 'https://{}.{}.cdn.digitaloceanspaces.com/{}'.format(os.getenv('DO_BUCKET'), os.getenv('DO_SPACES_REGION'), key)

            try:
                s3_client.head_object(Bucket=os.getenv('DO_BUCKET'), Key=key)

                # file exists

                update = [{
                    'range': 'C' + str(i),
                    'values': [['already archived']]
                }, {
                    'range': 'D' + str(i),
                    'values': [[cdn_url]]
                }]

                wks.batch_update(update)

            except ClientError:
                # Not found

                # sometimes this results in a different filename, so do this again
                info = ydl.extract_info(v[0], download=True)
                if 'entries' in info:
                    filename = ydl.prepare_filename(info['entries'][0])
                else:
                    filename = ydl.prepare_filename(info)

                print(filename)
                key = filename.split('/')[1]
                cdn_url = 'https://{}.{}.cdn.digitaloceanspaces.com/{}'.format(os.getenv('DO_BUCKET'), os.getenv('DO_SPACES_REGION'), key)

                # with open(filename, 'rb') as f:
                #     s3_client.upload_fileobj(f, Bucket=os.getenv('DO_BUCKET'), Key=key, ExtraArgs={'ACL': 'public-read'})

                os.remove(filename)

                update = [{
                    'range': 'C' + str(i),
                    'values': [['successful-desktop']]
                }, {
                    'range': 'B' + str(i),
                    'values': [[datetime.datetime.now().isoformat()]]
                }, {
                    'range': 'D' + str(i),
                    'values': [[cdn_url]]
                }]

                wks.batch_update(update)
        except:
            t, value, traceback = sys.exc_info()

            update = [{
                'range': 'C' + str(i),
                'values': [[str(value)]]
            }, {
                'range': 'B' + str(i),
                'values': [[datetime.datetime.now().isoformat()]]
            }]

            wks.batch_update(update)
