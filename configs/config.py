
import argparse, json
import gspread
from loguru import logger
from selenium import webdriver
from storages.local_storage import LocalStorage

from utils.gworksheet import GWorksheet
from storages import S3Config, S3Storage
from .wayback_config import WaybackConfig
from .telegram_config import TelegramConfig
from storages import Storage


class Config:
    """
    Controls the current execution parameters and manages API configurations
    Usage:
      c = Config() # initializes the argument parser
      c.parse() # parses the values and initializes the Services and API clients
      # you can then access the Services and APIs like
      c.s3_config

    """

    def __init__(self):
        self.parser = self.get_argument_parser()
        self.folder = ""

    def parse(self):
        self.args = self.parser.parse_args()
        logger.success(f'Command line arguments parsed successfully')
        self.config_file = self.args.config
        self.read_config_json()
        logger.info(f'APIs and Services initialized:\n{self}')

    def read_config_json(self):
        with open(self.config_file, "r", encoding="utf-8") as inf:
            self.config = json.load(inf)

        execution = self.config.get("execution", {})

        # general sheet configurations
        self.sheet = getattr(self.args, "sheet") or execution.get("sheet")
        assert self.sheet is not None, "'sheet' must be provided either through command line or configuration file"

        self.header = int(getattr(self.args, "header") or execution.get("header", 1))
        self.tmp_folder = execution.get("tmp_folder", Storage.TMP_FOLDER)
        Storage.TMP_FOLDER = self.tmp_folder

        self.storage = execution.get("storage", "s3")

        # Column names come from config and can be overwritten by CMD
        # in the end all are considered as lower case
        config_column_names = execution.get("column_names", {})
        self.column_names = {}
        for k in GWorksheet.COLUMN_NAMES.keys():
            self.column_names[k] = getattr(self.args, k) or config_column_names.get(k) or GWorksheet.COLUMN_NAMES[k]
        self.column_names = {k: v.lower() for k, v in self.column_names.items()}

        # selenium driver
        selenium_configs = execution.get("selenium", {})
        self.selenium_timeout = int(selenium_configs.get("timeout_seconds", 10))
        self.webdriver = "not initalized"

        # APIs and service configurations
        secrets = self.config.get("secrets", {})

        # google sheets config
        self.gsheets_client = gspread.service_account(
            filename=secrets.get("google_api", {}).get("filename", 'service_account.json')
        )

        # facebook config
        self.facebook_cookie = secrets.get("facebook", {}).get("cookie", None)

        # s3 config
        if "s3" in secrets:
            s3 = secrets["s3"]
            self.s3_config = S3Config(
                bucket=s3["bucket"],
                region=s3["region"],
                key=s3["key"],
                secret=s3["secret"]
            )
            self.s3_config.private = getattr(self.args, "private") or s3["private"] or self.s3_config.private
            self.s3_config.endpoint_url = s3["endpoint_url"] or self.s3_config.endpoint_url
            self.s3_config.cdn_url = s3["cdn_url"] or self.s3_config.cdn_url
            self.s3_config.key_path = s3["key_path"] or self.s3_config.key_path
            self.s3_config.no_folder = s3["no_folder"] or self.s3_config.no_folder
        else:
            logger.debug(f"'s3' key not present in the {self.config_file=}")

        # wayback machine config
        if "wayback" in secrets:
            self.wayback_config = WaybackConfig(
                key=secrets["wayback"]["key"],
                secret=secrets["wayback"]["secret"],
            )
        else:
            logger.debug(f"'wayback' key not present in the {self.config_file=}")

        # telethon config
        if "telegram" in secrets:
            self.telegram_config = TelegramConfig(
                api_id=secrets["telegram"]["api_id"],
                api_hash=secrets["telegram"]["api_hash"]
            )
        else:
            logger.debug(f"'telegram' key not present in the {self.config_file=}")

        del self.config["secrets"]

    def get_argument_parser(self):
        parser = argparse.ArgumentParser(description='Automatically archive social media videos from a Google Sheets document')

        parser.add_argument('--config', action='store', dest='config', help='the filename of the JSON configuration file (defaults to \'config.json\')', default='config.json')
        parser.add_argument('--sheet', action='store', dest='sheet', help='the name of the google sheets document [execution.sheet in config.json]')
        parser.add_argument('--header', action='store', dest='header', help='1-based index for the header row [execution.header in config.json]')
        parser.add_argument('--private', action='store_true', help='Store content without public access permission [execution.header in config.json]')

        for k, v in GWorksheet.COLUMN_NAMES.items():
            parser.add_argument(f'--col-{k}', action='store', dest=k, help=f'the name of the column to fill with {k} (default={v})')

        return parser

    def set_folder(self, folder):
        # update the folder in each of the storages
        self.folder = folder
        self.s3_config.folder = folder

    def get_storage(self):
        if self.storage == "s3":
            return S3Storage(self.s3_config)
        elif self.storage == "local":
            return LocalStorage(self.folder)
        raise f"storage {self.storage} not yet implemented"

    def destroy_webdriver(self):
        if self.webdriver is not None:
            self.webdriver.quit()

    def recreate_webdriver(self):
        options = webdriver.FirefoxOptions()
        options.headless = True
        options.set_preference('network.protocol-handler.external.tg', False)
        self.webdriver = webdriver.Firefox(options=options)
        self.webdriver.set_window_size(1400, 2000)
        self.webdriver.set_page_load_timeout(self.selenium_timeout)

    def __str__(self) -> str:
        return json.dumps({
            "config_file": self.config_file,
            "sheet": self.sheet,
            "header": self.header,
            "tmp_folder": self.tmp_folder,
            "selenium_timeout_seconds": self.selenium_timeout,
            "selenium_webdriver": self.webdriver != None,
            "s3_config": self.s3_config != None,
            "s3_private": getattr(self.s3_config, "private", None),
            "wayback_config": self.wayback_config != None,
            "telegram_config": self.telegram_config != None,
            "gsheets_client": self.gsheets_client != None,
            "column_names": self.column_names,
        }, ensure_ascii=False, indent=4)
