<h1 align="center">Auto Archiver</h1>

[![Documentation Status](https://readthedocs.org/projects/auto-archiver/badge/?version=latest)](https://auto-archiver.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/auto-archiver.svg)](https://badge.fury.io/py/auto-archiver)
[![Docker Image Version (latest by date)](https://img.shields.io/docker/v/bellingcat/auto-archiver?sort=semver&logo=docker&color=#69F0AE)](https://hub.docker.com/r/bellingcat/auto-archiver)
[![Core Test Status](https://github.com/bellingcat/auto-archiver/workflows/Core%20Tests/badge.svg)](https://github.com/bellingcat/auto-archiver/actions/workflows/tests-core.yaml)
<!-- [![Download Test Status](https://github.com/bellingcat/auto-archiver/workflows/Download%20Tests/badge.svg)](https://github.com/bellingcat/auto-archiver/actions/workflows/tests-download.yaml) -->

<!-- ![Docker Pulls](https://img.shields.io/docker/pulls/bellingcat/auto-archiver) -->
<!-- [![PyPI download month](https://img.shields.io/pypi/dm/auto-archiver.svg)](https://pypi.python.org/pypi/auto-archiver/) -->



Auto Archiver is a Python tool to automatically archive content on the web in a secure and verifiable way. It takes URLs from different sources (e.g. a CSV file, Google Sheets, command line etc.) and archives the content of each one. It can archive social media posts, videos, images and webpages. Content can be enriched, then saved either locally or remotely (S3 bucket, Google Drive). The status of the archiving process can be appended to a CSV report, or if using Google Sheets – back to the original sheet.

<div class="hidden_rtd">
  
**[See the Auto Archiver documentation for more information.](https://auto-archiver.readthedocs.io/en/latest/)**

</div>

Read the [article about Auto Archiver on bellingcat.com](https://www.bellingcat.com/resources/2022/09/22/preserve-vital-online-content-with-bellingcats-auto-archiver-tool/).


## One-Click Cloud Deploy

Deploy your own Auto Archiver instance to the cloud — no coding required:

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/bellingcat/auto-archiver&envs=AUTH_PASSWORD,GSHEET_URL,GOOGLE_SERVICE_ACCOUNT_JSON,POLL_INTERVAL,S3_BUCKET,S3_KEY,S3_SECRET,S3_REGION,TELEGRAM_API_ID,TELEGRAM_API_HASH,TELEGRAM_BOT_TOKEN,ENABLE_SCREENSHOTS,LOG_LEVEL&optionalEnvs=GSHEET_URL,GOOGLE_SERVICE_ACCOUNT_JSON,POLL_INTERVAL,S3_BUCKET,S3_KEY,S3_SECRET,S3_REGION,TELEGRAM_API_ID,TELEGRAM_API_HASH,TELEGRAM_BOT_TOKEN,ENABLE_SCREENSHOTS,LOG_LEVEL&AUTH_PASSWORDDesc=Password+to+access+your+archiver+web+interface&GSHEET_URLDesc=Google+Sheet+URL+to+monitor+for+new+URLs+(leave+empty+to+disable)&POLL_INTERVALDesc=Seconds+between+Google+Sheet+checks+(min+60)&POLL_INTERVALDefault=300&S3_BUCKETDesc=S3+bucket+name+for+storage+(leave+empty+for+local+only)&S3_REGIONDefault=us-east-1&LOG_LEVELDefault=INFO)

**What you get:** A web interface where you can paste URLs and archive them instantly. Optionally connect a Google Sheet for automated monitoring, S3 for cloud storage, and Telegram for archiving channels.

**Only required setting:** `AUTH_PASSWORD` — everything else is optional and can be configured later via the Railway dashboard.

<details>
<summary>📋 Environment variables reference</summary>

| Variable | Required | Description |
|----------|----------|-------------|
| `AUTH_PASSWORD` | **Yes** | Password to access the web interface |
| `GSHEET_URL` | No | Google Sheet URL to monitor for new URLs [use this template](https://docs.google.com/spreadsheets/d/1NJZo_XZUBKTI1Ghlgi4nTPVvCfb0HXAs6j5tNGas72k/edit?gid=0#gid=0) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | No | Google service account JSON (required with Sheets) [follow these instructions](https://auto-archiver.readthedocs.io/en/v1.0.1/how_to/gsheets_setup.html) |
| `POLL_INTERVAL` | No | Seconds between Sheet checks (default: 300) |
| `S3_BUCKET` | No | S3 bucket name for archived content, ideal for cloud hosting your archives but not mandatory, any S3-compatible storage works |
| `S3_KEY` / `S3_SECRET` | No | S3 credentials |
| `S3_REGION` | No | S3 region (default: us-east-1) |
| `S3_ENDPOINT` | No | S3 endpoint URL |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | No | Telegram API credentials |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token |
| `ENABLE_SCREENSHOTS` | No | Set to `true` for full-page screenshots |
| `ENABLE_THUMBNAILS` | No | Set to `true` for video thumbnails |
| `ENABLE_CSV_DB` | No | Set to `true` for CSV logging |
| `LOG_LEVEL` | No | DEBUG, INFO, WARNING, ERROR (default: INFO) |

</details>


## Traditional Installation

View the [Installation Guide](https://auto-archiver.readthedocs.io/en/latest/installation/installation.html) for full instructions

**Advanced:**

To get started quickly using Docker:

`docker pull bellingcat/auto-archiver && docker run -it --rm -v secrets:/app/secrets bellingcat/auto-archiver --config secrets/orchestration.yaml`

Or pip:

`pip install auto-archiver && auto-archiver --help`

## Contributing

We welcome contributions to the Auto Archiver project! See the [Contributing Guide](https://auto-archiver.readthedocs.io/en/latest/contributing.html) for how to get involved!

