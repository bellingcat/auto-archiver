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

load_dotenv()


options = webdriver.FirefoxOptions()
options.headless = True
driver = webdriver.Firefox(options=options)
driver.set_window_size(1400, 2000)

s3_config = S3Config(
    bucket=os.getenv('DO_BUCKET'),
    region=os.getenv('DO_SPACES_REGION'),
    key=os.getenv('DO_SPACES_KEY'),
    secret=os.getenv('DO_SPACES_SECRET'),
    folder="temp"
)
s3_client = S3Storage(s3_config)
telegram_config = archivers.TelegramConfig(
    api_id=os.getenv('TELEGRAM_API_ID'),
    api_hash=os.getenv('TELEGRAM_API_HASH')
)

archiver = archivers.TelethonArchiver(s3_client, driver, telegram_config)

URLs = [
    # "https://t.me/c/1226032830/24864",
    # "https://t.me/truexanewsua/32650",
    "https://t.me/informatsia_obstanovka/5239",
    # "https://t.me/informatsia_obstanovka/5240",
    # "https://t.me/informatsia_obstanovka/5241",
    # "https://t.me/informatsia_obstanovka/5242"
]


for url in URLs:
    print(url)
    print(archiver.download(url, False))
