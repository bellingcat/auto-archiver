""" Orchestrates all archiving steps, including feeding items,
    archiving them with specific archivers, enrichment, storage,
    formatting, database operations and clean up.

"""

from __future__ import annotations
import ast
import os
from os.path import dirname, join
from typing import Generator, Union, List
from urllib.parse import urlparse
from ipaddress import ip_address
import argparse

from .context import ArchivingContext

from ..archivers import Archiver
from ..feeders import Feeder
from ..formatters import Formatter
from ..storages import Storage
from ..enrichers import Enricher
from ..databases import Database
from .metadata import Metadata
from ..version import __version__
from .config import read_yaml
from .loader import available_modules, load_manifest

import tempfile, traceback
from loguru import logger


DEFAULT_CONFIG_FILE = "orchestration.yaml"
class ArchivingOrchestrator:

    # def __init__(self, config: Config) -> None:
    #     self.feeder: Feeder = config.feeder
    #     self.formatter: Formatter = config.formatter
    #     self.enrichers: List[Enricher] = config.enrichers
    #     self.archivers: List[Archiver] = config.archivers
    #     self.databases: List[Database] = config.databases
    #     self.storages: List[Storage] = config.storages
    #     ArchivingContext.set("storages", self.storages, keep_on_reset=True)

    #     try: 
    #         for a in self.all_archivers_for_setup(): a.setup()
    #     except (KeyboardInterrupt, Exception) as e:
    #         logger.error(f"Error during setup of archivers: {e}\n{traceback.format_exc()}")
    #         self.cleanup()

    def setup_parser(self):
        parser = argparse.ArgumentParser(
                # prog = "auto-archiver",
                description="Auto Archiver is a CLI tool to archive media/metadata from online URLs; it can read URLs from many sources (Google Sheets, Command Line, ...); and write results to many destinations too (CSV, Google Sheets, MongoDB, ...)!",
                epilog="Check the code at https://github.com/bellingcat/auto-archiver"
        )
        parser.add_argument('--config', action='store', dest='config_file', help='the filename of the YAML configuration file (defaults to \'config.yaml\')', default=DEFAULT_CONFIG_FILE)
        parser.add_argument('--version', action='version', version=__version__)
        parser.add_argument('--mode', action='store', dest='mode', type=str, choices=['simple', 'full'], help='the mode to run the archiver in', default='simple')
        self.parser = parser
    
    def setup_config(self):
        # check what mode we're in
        # if simple, we'll load just the modules that has requires_setup = False
        # if full, we'll load all modules
        if self.config.mode == 'simple':
            for module in available_modules():
                # load the module
                manifest = load_manifest(module)
                

    def run(self) -> None:
        self.setup_parser()

        # parse the known arguments for now (basically, we want the config file)

        # load the config file to get the list of enabled items
        self.config, _ = self.parser.parse_known_args()

        # load the config file
        try:
            config = read_yaml(self.config.config_file)
        except FileNotFoundError:
            if self.settings.config == DEFAULT_CONFIG_FILE:
                # no config file found, let's do the setup with the default values
                self.setup_config()
            else:
                logger.error(f"The configuration file {self.config.config_file} was  not found. Make sure the file exists and try again, or run without the --config file to use the default settings.")
                exit()

        breakpoint()
        config.parse()


        for item in self.feed():
            pass

    def cleanup(self)->None:
        logger.info("Cleaning up")
        for a in self.all_archivers_for_setup(): a.cleanup()

    def feed(self) -> Generator[Metadata]:
        for item in self.feeder:
            yield self.feed_item(item)
        self.cleanup()

    def feed_item(self, item: Metadata) -> Metadata:
        """
        Takes one item (URL) to archive and calls self.archive, additionally:
            - catches keyboard interruptions to do a clean exit
            - catches any unexpected error, logs it, and does a clean exit
        """
        try:
            ArchivingContext.reset()
            with tempfile.TemporaryDirectory(dir="./") as tmp_dir:
                ArchivingContext.set_tmp_dir(tmp_dir)
                return self.archive(item)
        except KeyboardInterrupt:
            # catches keyboard interruptions to do a clean exit
            logger.warning(f"caught interrupt on {item=}")
            for d in self.databases: d.aborted(item)
            self.cleanup()
            exit()
        except Exception as e:
            logger.error(f'Got unexpected error on item {item}: {e}\n{traceback.format_exc()}')
            for d in self.databases:
                if type(e) == AssertionError: d.failed(item, str(e))
                else: d.failed(item)


    def archive(self, result: Metadata) -> Union[Metadata, None]:
        """
            Runs the archiving process for a single URL
            1. Each archiver can sanitize its own URLs
            2. Check for cached results in Databases, and signal start to the databases
            3. Call Archivers until one succeeds
            4. Call Enrichers
            5. Store all downloaded/generated media
            6. Call selected Formatter and store formatted if needed
        """
        original_url = result.get_url().strip()
        self.assert_valid_url(original_url)

        # 1 - sanitize - each archiver is responsible for cleaning/expanding its own URLs
        url = original_url
        for a in self.archivers: url = a.sanitize_url(url)
        result.set_url(url)
        if original_url != url: result.set("original_url", original_url)

        # 2 - notify start to DBs, propagate already archived if feature enabled in DBs
        cached_result = None
        for d in self.databases:
            d.started(result)
            if (local_result := d.fetch(result)):
                cached_result = (cached_result or Metadata()).merge(local_result)
        if cached_result:
            logger.debug("Found previously archived entry")
            for d in self.databases:
                try: d.done(cached_result, cached=True)
                except Exception as e:
                    logger.error(f"ERROR database {d.name}: {e}: {traceback.format_exc()}")
            return cached_result

        # 3 - call archivers until one succeeds
        for a in self.archivers:
            logger.info(f"Trying archiver {a.name} for {url}")
            try:
                result.merge(a.download(result))
                if result.is_success(): break
            except Exception as e: 
                logger.error(f"ERROR archiver {a.name}: {e}: {traceback.format_exc()}")

        # 4 - call enrichers to work with archived content
        for e in self.enrichers:
            try: e.enrich(result)
            except Exception as exc: 
                logger.error(f"ERROR enricher {e.name}: {exc}: {traceback.format_exc()}")

        # 5 - store all downloaded/generated media
        result.store()

        # 6 - format and store formatted if needed
        if (final_media := self.formatter.format(result)):
            final_media.store(url=url, metadata=result)
            result.set_final_media(final_media)

        if result.is_empty():
            result.status = "nothing archived"

        # signal completion to databases and archivers
        for d in self.databases:
            try: d.done(result)
            except Exception as e:
                logger.error(f"ERROR database {d.name}: {e}: {traceback.format_exc()}")

        return result

    def assert_valid_url(self, url: str) -> bool:
        """
        Blocks localhost, private, reserved, and link-local IPs and all non-http/https schemes.
        """
        assert url.startswith("http://") or url.startswith("https://"), f"Invalid URL scheme"
        
        parsed = urlparse(url)
        assert parsed.scheme in ["http", "https"], f"Invalid URL scheme"
        assert parsed.hostname, f"Invalid URL hostname"
        assert parsed.hostname != "localhost", f"Invalid URL"

        try: # special rules for IP addresses
            ip = ip_address(parsed.hostname)
        except ValueError: pass
        else:
            assert ip.is_global, f"Invalid IP used"
            assert not ip.is_reserved, f"Invalid IP used"
            assert not ip.is_link_local, f"Invalid IP used"
            assert not ip.is_private, f"Invalid IP used"

    def all_archivers_for_setup(self) -> List[Archiver]:
        return self.archivers + [e for e in self.enrichers if isinstance(e, Archiver)]