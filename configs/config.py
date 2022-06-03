
import argparse, json
import gspread
from loguru import logger
from selenium import webdriver
from dataclasses import dataclass

from utils.gworksheet import GWorksheet
from .wayback_config import WaybackConfig
from .telegram_config import TelegramConfig
from storages import Storage, S3Config, S3Storage, GDStorage, GDConfig, LocalStorage


@dataclass
class SeleniumConfig:
    timeout_seconds: int = 120
    window_width: int = 1400
    window_height: int = 2000


class Config:
    """
    Controls the current execution parameters and manages API configurations
    Usage:
      c = Config() # initializes the argument parser
      c.parse() # parses the values and initializes the Services and API clients
      # you can then access the Services and APIs like
      c.s3_config
    All the configurations available as cmd line options, when included, will 
    override the configurations in the config.json file.
    Configurations are split between:
    1. "secrets" containing API keys for generating services - not kept in memory
    2. "execution" containing specific execution configurations
    """
    AVAILABLE_STORAGES = {"s3", "gd", "local"}

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

        # ----------------------EXECUTION - execution configurations
        execution = self.config.get("execution", {})

        self.sheet = getattr(self.args, "sheet", execution.get("sheet"))
        assert self.sheet is not None, "'sheet' must be provided either through command line or configuration file"
        self.header = int(getattr(self.args, "header", execution.get("header", 1)))
        Storage.TMP_FOLDER = execution.get("tmp_folder", Storage.TMP_FOLDER)
        self.storage = getattr(self.args, "storage", execution.get("storage", "s3"))

        for key, name in [("s3", "s3"), ("gd", "google_drive")]:
            assert self.storage != key or name in secrets, f"selected storage '{key}' requires secrets.'{name}' in {self.config_file}"

        # Column names come from config and can be overwritten by CMD
        # in the end all are considered as lower case
        config_column_names = execution.get("column_names", {})
        self.column_names = {}
        for k in GWorksheet.COLUMN_NAMES.keys():
            self.column_names[k] = getattr(self.args, k, config_column_names.get(k, GWorksheet.COLUMN_NAMES[k])).lower()

        # selenium driver
        selenium_configs = execution.get("selenium", {})
        self.selenium_config = SeleniumConfig(
            timeout_seconds=int(selenium_configs.get("timeout_seconds", SeleniumConfig.timeout_seconds)),
            window_width=int(selenium_configs.get("window_width", SeleniumConfig.window_width)),
            window_height=int(selenium_configs.get("window_height", SeleniumConfig.window_height))
        )
        self.webdriver = "not initalized"

        # ---------------------- SECRETS - APIs and service configurations
        secrets = self.config.get("secrets", {})

        # google sheets config
        self.gsheets_client = gspread.service_account(
            filename=secrets.get("google_sheets", {}).get("service_account", 'service_account.json')
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
                secret=s3["secret"],
                endpoint_url=s3.get("endpoint_url", S3Config.endpoint_url),
                cdn_url=s3.get("cdn_url", S3Config.cdn_url),
                key_path=s3.get("key_path", S3Config.key_path),
                private=getattr(self.args, "s3-private", s3.get("private", S3Config.private)),
                no_folder=s3.get("no_folder", S3Config.no_folder),
            )

        # GDrive config
        if "google_drive" in secrets:
            gd = secrets["google_drive"]
            self.gd_config = GDConfig(
                root_folder_id=gd.get("root_folder_id"),
                default_folder=gd.get("default_folder", GDConfig.default_folder),
                service_account=gd.get("service_account", GDConfig.service_account),
            )

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

        del self.config["secrets"]  # delete to prevent leaks

    def get_argument_parser(self):
        """
        Creates the CMD line arguments. 'python auto_archive.py --help'
        """
        parser = argparse.ArgumentParser(description='Automatically archive social media posts, videos, and images from a Google Sheets document. The command line arguments will always override the configurations in the provided JSON config file (--config), only some high-level options are allowed via the command line and the JSON configuration file is the preferred method. ')

        parser.add_argument('--config', action='store', dest='config', help='the filename of the JSON configuration file (defaults to \'config.json\')', default='config.json')
        parser.add_argument('--storage', action='store', dest='storage', help='which storage to use [execution.storage in config.json]', choices=Config.AVAILABLE_STORAGES)
        parser.add_argument('--sheet', action='store', dest='sheet', help='the name of the google sheets document [execution.sheet in config.json]')
        parser.add_argument('--header', action='store', dest='header', help='1-based index for the header row [execution.header in config.json]')
        parser.add_argument('--s3-private', action='store_true', help='Store content without public access permission (only for storage=s3) [secrets.s3.private in config.json]')

        for k, v in GWorksheet.COLUMN_NAMES.items():
            parser.add_argument(f'--col-{k}', action='store', dest=k, help=f"name of the column to fill with {k} (default='{v}')")

        return parser

    def set_folder(self, folder):
        # update the folder in each of the storages
        self.folder = folder
        if self.s3_config:
            self.s3_config.folder = folder
        if self.gd_config:
            self.gd_config.default_folder = folder

    def get_storage(self):
        """
        creates and returns the configured type of storage
        """
        if self.storage == "s3":
            return S3Storage(self.s3_config)
        elif self.storage == "gd":
            return GDStorage(self.gd_config)
        elif self.storage == "local":
            return LocalStorage(self.folder)
        raise f"storage {self.storage} not implemented, available: {Config.AVAILABLE_STORAGES}"

    def destroy_webdriver(self):
        if self.webdriver is not None and type(self.webdriver) != str:
            self.webdriver.quit()

    def recreate_webdriver(self):
        self.destroy_webdriver()
        options = webdriver.FirefoxOptions()
        options.headless = True
        options.set_preference('network.protocol-handler.external.tg', False)
        self.webdriver = webdriver.Firefox(options=options)
        self.webdriver.set_window_size(self.selenium_config.window_width,
                                       self.selenium_config.window_height)
        self.webdriver.set_page_load_timeout(self.selenium_config.timeout_seconds)

    def __str__(self) -> str:
        return json.dumps({
            "config_file": self.config_file,
            "sheet": self.sheet,
            "header": self.header,
            "tmp_folder": Storage.TMP_FOLDER,
            "selenium_config": self.selenium_config,
            "selenium_webdriver": self.webdriver != None,
            "s3_config": self.s3_config != None,
            "s3_private": getattr(self.s3_config, "private", None),
            "wayback_config": self.wayback_config != None,
            "telegram_config": self.telegram_config != None,
            "gsheets_client": self.gsheets_client != None,
            "column_names": self.column_names,
        }, ensure_ascii=False, indent=4)
