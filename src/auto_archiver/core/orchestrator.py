""" Orchestrates all archiving steps, including feeding items,
    archiving them with specific archivers, enrichment, storage,
    formatting, database operations and clean up.

"""

from __future__ import annotations
from typing import Generator, Union, List
from urllib.parse import urlparse
from ipaddress import ip_address
import argparse
import os
import sys

from rich_argparse import RichHelpFormatter

from .context import ArchivingContext

from .metadata import Metadata
from ..version import __version__
from .config import read_yaml, store_yaml, to_dot_notation, merge_dicts, EMPTY_CONFIG
from .loader import available_modules, Module, MODULE_TYPES, load_module
from . import validators

import tempfile, traceback
from loguru import logger


DEFAULT_CONFIG_FILE = "orchestration.yaml"

class UniqueAppendAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not hasattr(namespace, self.dest):
            setattr(namespace, self.dest, [])
        for value in values:
            if value not in getattr(namespace, self.dest):
                getattr(namespace, self.dest).append(value)

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

    def setup_basic_parser(self):
        parser = argparse.ArgumentParser(
                add_help=False,
                description="""
                Auto Archiver is a CLI tool to archive media/metadata from online URLs;
                it can read URLs from many sources (Google Sheets, Command Line, ...); and write results to many destinations too (CSV, Google Sheets, MongoDB, ...)!
                """,
                epilog="Check the code at https://github.com/bellingcat/auto-archiver",
                formatter_class=RichHelpFormatter,
        )
        parser.add_argument('--config', action='store', dest="config_file", help='the filename of the YAML configuration file (defaults to \'config.yaml\')', default=DEFAULT_CONFIG_FILE)
        parser.add_argument('--version', action='version', version=__version__)
        parser.add_argument('--mode', action='store', dest='mode', type=str, choices=['simple', 'full'], help='the mode to run the archiver in', default='simple')
        # override the default 'help' so we can inject all the configs and show those
        parser.add_argument('-h', '--help', action='store_true', dest='help', help='show this help message and exit')
        parser.add_argument('-s', '--store', dest='store', default=True, help='Store the created config in the config file', action=argparse.BooleanOptionalAction)

        self.basic_parser = parser

    def setup_complete_parser(self, basic_config: dict, yaml_config: dict, unused_args: list[str]) -> None:
        parser = argparse.ArgumentParser(
            add_help=False,
        )
        self.add_additional_args(parser)

        # check what mode we're in
        # if we have a config file, use that to decide which modules to load
        # if simple, we'll load just the modules that has requires_setup = False
        # if full, we'll load all modules
        # TODO: BUG** - basic_config won't have steps in it, since these args aren't added to 'basic_parser'
        # but should we add them? Or should we just add them to the 'complete' parser?
        if yaml_config != EMPTY_CONFIG:
            # only load the modules enabled in config
            # TODO: if some steps are empty (e.g. 'feeders' is empty), should we default to the 'simple' ones? Or only if they are ALL empty?
            enabled_modules = []
            for module_type in MODULE_TYPES:
                enabled_modules.extend(yaml_config['steps'].get(f"{module_type}s", []))

            # add in any extra modules that have been passed on the command line for 'feeders', 'enrichers', 'archivers', 'databases', 'storages', 'formatter'
            for module_type in MODULE_TYPES:
                if modules := getattr(basic_config, f"{module_type}s", []):
                    enabled_modules.extend(modules)

            self.add_module_args(available_modules(with_manifest=True, limit_to_modules=set(enabled_modules), suppress_warnings=True), parser)
        elif basic_config.mode == 'simple':
            simple_modules = [module for module in available_modules(with_manifest=True) if not module.requires_setup]
            self.add_module_args(simple_modules, parser)
            # add them to the config
            for module in simple_modules:
                for module_type in module.type:
                    yaml_config['steps'].setdefault(f"{module_type}s", []).append(module.name)
        else:
            # load all modules, they're not using the 'simple' mode
            self.add_module_args(available_modules(with_manifest=True), parser)
        
        parser.set_defaults(**to_dot_notation(yaml_config))

        # reload the parser with the new arguments, now that we have them
        parsed, unknown = parser.parse_known_args(unused_args)

        # merge the new config with the old one
        self.config = merge_dicts(vars(parsed), yaml_config)
        # clean out args from the base_parser that we don't want in the config
        for key in vars(basic_config):
            self.config.pop(key, None)

        # setup the logging
        self.setup_logging()

        if unknown:
            logger.warning(f"Ignoring unknown/unused arguments: {unknown}\nPerhaps you don't have this module enabled?")

        if (self.config != yaml_config and basic_config.store) or not os.path.isfile(basic_config.config_file):
            logger.info(f"Storing configuration file to {basic_config.config_file}")
            store_yaml(self.config, basic_config.config_file)
        
        return self.config
    
    def add_additional_args(self, parser: argparse.ArgumentParser = None):
        if not parser:
            parser = self.parser

        parser.add_argument('--feeders', dest='steps.feeders', nargs='+', help='the feeders to use', action=UniqueAppendAction)
        parser.add_argument('--enrichers', dest='steps.enrichers',  nargs='+', help='the enrichers to use', action=UniqueAppendAction)
        parser.add_argument('--extractors', dest='steps.extractors', nargs='+', help='the extractors to use', action=UniqueAppendAction)
        parser.add_argument('--databases', dest='steps.databases', nargs='+', help='the databases to use', action=UniqueAppendAction)
        parser.add_argument('--storages', dest='steps.storages', nargs='+', help='the storages to use', action=UniqueAppendAction)
        parser.add_argument('--formatters', dest='steps.formatters', nargs='+', help='the formatter to use', action=UniqueAppendAction)

        # logging arguments
        parser.add_argument('--logging.level', action='store', dest='logging.level', choices=['INFO', 'DEBUG', 'ERROR', 'WARNING'], help='the logging level to use', default='INFO')
        parser.add_argument('--logging.file', action='store', dest='logging.file', help='the logging file to write to', default=None)
        parser.add_argument('--logging.rotation', action='store', dest='logging.rotation', help='the logging rotation to use', default=None)

    def add_module_args(self, modules: list[Module] = None, parser: argparse.ArgumentParser = None):

        if not modules:
            modules = available_modules(with_manifest=True)

        module: Module
        for module in modules:
            if not module.configs:
                # this module has no configs, don't show anything in the help
                # (TODO: do we want to show something about this module though, like a description?)
                continue
            group = parser.add_argument_group(module.display_name or module.name, f"{module.description[:100]}...")
            for name, kwargs in module.configs.items():
                # TODO: go through all the manifests and make sure we're not breaking anything with removing cli_set
                # in most cases it'll mean replacing it with 'type': 'str' or 'type': 'int' or something
                kwargs.pop('cli_set', None)
                kwargs['dest'] = f"{module.name}.{kwargs.pop('dest', name)}"
                try:
                    kwargs['type'] = __builtins__.get(kwargs.get('type'), str)
                except KeyError:
                    kwargs['type'] = getattr(validators, kwargs['type'])
                group.add_argument(f"--{module.name}.{name}", **kwargs)

    def show_help(self):
        # for the help message, we want to load *all* possible modules and show the help
            # add configs as arg parser arguments
        
        self.add_additional_args(self.basic_parser)
        self.add_module_args(parser=self.basic_parser)

        self.basic_parser.print_help()
        exit()
    
    def setup_logging(self):
        # setup loguru logging
        logger.remove() # remove the default logger
        logging_config = self.config['logging']
        logger.add(sys.stderr, level=logging_config['level'])
        if log_file := logging_config['file']:
            logger.add(log_file, rotation=logging_config['logging.rotation'])

        
    def install_modules(self):
        """
        Swaps out the previous 'strings' in the config with the actual modules
        """
        
        invalid_modules = []
        for module_type in MODULE_TYPES:
            step_items = []
            modules_to_load = self.config['steps'][f"{module_type}s"]

            def check_steps_ok():
                if not len(step_items):
                    logger.error(f"NO {module_type.upper()}S LOADED. Please check your configuration and try again.")
                    if len(modules_to_load):
                        logger.error(f"Tried to load the following modules, but none were available: {modules_to_load}")
                    exit()

                if (module_type == 'feeder' or module_type == 'formatter') and len(step_items) > 1:
                    logger.error(f"Only one {module_type} is allowed, found {len(step_items)} {module_type}s. Please remove one of the following from your configuration file: {modules_to_load}")
                    exit()

            for i, module in enumerate(modules_to_load):
                if module in invalid_modules:
                    continue
                loaded_module = load_module(module)
                if not loaded_module:
                    invalid_modules.append(module)
                    continue
                if loaded_module:
                    step_items.append(loaded_module)
            check_steps_ok()
            self.config['steps'][f"{module_type}s"] = step_items
            

            assert len(step_items) > 0, f"No {module_type}s were loaded. Please check your configuration file and try again."
            self.config['steps'][f"{module_type}s"] = step_items

    def run(self) -> None:
        self.setup_basic_parser()

        # parse the known arguments for now (basically, we want the config file)

        # load the config file to get the list of enabled items
        basic_config, unused_args = self.basic_parser.parse_known_args()

        # if help flag was called, then show the help
        if basic_config.help:
            self.show_help()

        # load the config file
        yaml_config = {}

        if not os.path.exists(basic_config.config_file) and basic_config.config_file != DEFAULT_CONFIG_FILE:
            logger.error(f"The configuration file {basic_config.config_file} was  not found. Make sure the file exists and try again, or run without the --config file to use the default settings.")
            exit()

        yaml_config = read_yaml(basic_config.config_file)
            

        self.setup_complete_parser(basic_config, yaml_config, unused_args)
        
        self.install_modules()

        logger.info("FEEDERS: " + ", ".join(m.name for m in self.config['steps']['feeders']))
        logger.info("EXTRACTORS: " + ", ".join(m.name for m in self.config['steps']['extractors']))
        logger.info("ENRICHERS: " + ", ".join(m.name for m in self.config['steps']['enrichers']))
        logger.info("DATABASES: " + ", ".join(m.name for m in self.config['steps']['databases']))
        logger.info("STORAGES: " + ", ".join(m.name for m in self.config['steps']['storages']))
        logger.info("FORMATTERS: " + ", ".join(m.name for m in self.config['steps']['formatters']))

        for item in self.feed():
            pass

    def cleanup(self)->None:
        logger.info("Cleaning up")
        for e in self.config['steps']['extractors']:
            e.cleanup()

    def feed(self) -> Generator[Metadata]:
        for feeder in self.config['steps']['feeders']:
            for item in feeder:
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
            for d in self.config['steps']['databases']: d.aborted(item)
            self.cleanup()
            exit()
        except Exception as e:
            logger.error(f'Got unexpected error on item {item}: {e}\n{traceback.format_exc()}')
            for d in self.config['steps']['databases']:
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