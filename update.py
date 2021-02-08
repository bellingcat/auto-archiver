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
sh = gc.open("Media Sheet (January 16-20 + People)")

# loop through worksheets to check
for ii in range(5):
    wks = sh.get_worksheet(ii)
    values = wks.get_all_values()

    ydl_opts = {'outtmpl': 'tmp/%(id)s.%(ext)s', 'quiet': False}
    ydl = youtube_dl.YoutubeDL(ydl_opts)

    s3_client = boto3.client('s3',
            region_name=os.getenv('DO_SPACES_REGION'),
            endpoint_url='https://{}.digitaloceanspaces.com'.format(os.getenv('DO_SPACES_REGION')),
            aws_access_key_id=os.getenv('DO_SPACES_KEY'),
            aws_secret_access_key=os.getenv('DO_SPACES_SECRET'))

    # loop through rows in worksheet
    for i in range(2, len(values)+1):
        v = values[i-1]

        if v[1] != "" and v[10] == "":
            print(v[1])

            try:
                info = ydl.extract_info(v[1], download=False)

                # skip if live
                if 'is_live' not in info or not info['is_live']:
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
                            'range': 'K' + str(i),
                            'values': [['already archived']]
                        }, {
                            'range': 'M' + str(i),
                            'values': [[cdn_url]]
                        }]

                        wks.batch_update(update)

                    except ClientError:
                        # Not found

                        # sometimes this results in a different filename, so do this again
                        info = ydl.extract_info(v[1], download=True)
                        if 'entries' in info:
                            filename = ydl.prepare_filename(info['entries'][0])
                        else:
                            filename = ydl.prepare_filename(info)


                        if not os.path.exists(filename):
                            filename = filename.split('.')[0] + '.mkv'

                        print(filename)
                        key = filename.split('/')[1]
                        cdn_url = 'https://{}.{}.cdn.digitaloceanspaces.com/{}'.format(os.getenv('DO_BUCKET'), os.getenv('DO_SPACES_REGION'), key)

                        with open(filename, 'rb') as f:
                            s3_client.upload_fileobj(f, Bucket=os.getenv('DO_BUCKET'), Key=key, ExtraArgs={'ACL': 'public-read'})

                        os.remove(filename)

                        update = [{
                            'range': 'K' + str(i),
                            'values': [['successful']]
                        }, {
                            'range': 'L' + str(i),
                            'values': [[datetime.datetime.now().isoformat()]]
                        }, {
                            'range': 'M' + str(i),
                            'values': [[cdn_url]]
                        }]

                        wks.batch_update(update)
            except:
                t, value, traceback = sys.exc_info()

                update = [{
                    'range': 'K' + str(i),
                    'values': [[str(value)]]
                }, {
                    'range': 'L' + str(i),
                    'values': [[datetime.datetime.now().isoformat()]]
                }]

                wks.batch_update(update)
