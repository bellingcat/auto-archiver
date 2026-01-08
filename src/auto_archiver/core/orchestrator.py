"""Orchestrates all archiving steps, including feeding items,
archiving them with specific archivers, enrichment, storage,
formatting, database operations and clean up.

"""

from __future__ import annotations
from packaging import version
from typing import Generator, Union, List, Type, TYPE_CHECKING
import argparse
import os
import sys
from tempfile import TemporaryDirectory
import traceback
from copy import copy

from rich_argparse import RichHelpFormatter
from auto_archiver.utils.custom_logger import format_for_human_readable_console, logger
import requests

from auto_archiver.utils.misc import random_str

from .metadata import Metadata, Media
from auto_archiver.version import __version__
from .config import (
    read_yaml,
    store_yaml,
    to_dot_notation,
    merge_dicts,
    is_valid_config,
    DefaultValidatingParser,
    UniqueAppendAction,
    AuthenticationJsonParseAction,
    DEFAULT_CONFIG_FILE,
)
from .module import ModuleFactory, LazyBaseModule
from . import validators, Feeder, Extractor, Database, Storage, Formatter, Enricher
from .consts import MODULE_TYPES, SetupError
from auto_archiver.utils.url import check_url_or_raise, clean

if TYPE_CHECKING:
    from .base_module import BaseModule
    from .module import LazyBaseModule


class ArchivingOrchestrator:
    # instance variables
    module_factory: ModuleFactory
    setup_finished: bool
    logger_id: int

    # instance variables, used for convenience to access modules by step
    feeders: List[Type[Feeder]]
    extractors: List[Type[Extractor]]
    enrichers: List[Type[Enricher]]
    databases: List[Type[Database]]
    storages: List[Type[Storage]]
    formatters: List[Type[Formatter]]

    def __init__(self):
        self.module_factory = ModuleFactory()
        self.setup_finished = False
        self.logger_id = None

    def setup_basic_parser(self):
        parser = argparse.ArgumentParser(
            prog="auto-archiver",
            add_help=False,
            description="""
                Auto Archiver is a CLI tool to archive media/metadata from online URLs;
                it can read URLs from many sources (Google Sheets, Command Line, ...); and write results to many destinations too (CSV, Google Sheets, MongoDB, ...)!
                """,
            epilog="Check the code at https://github.com/bellingcat/auto-archiver",
            formatter_class=RichHelpFormatter,
        )
        parser.add_argument("--help", "-h", action="store_true", dest="help", help="show a full help message and exit")
        parser.add_argument("--version", action="version", version=__version__)
        parser.add_argument(
            "--config",
            action="store",
            dest="config_file",
            help="the filename of the YAML configuration file (defaults to 'config.yaml')",
            default=DEFAULT_CONFIG_FILE,
        )
        parser.add_argument(
            "--mode",
            action="store",
            dest="mode",
            type=str,
            choices=["simple", "full"],
            help="the mode to run the archiver in",
            default="simple",
        )
        # override the default 'help' so we can inject all the configs and show those
        parser.add_argument(
            "-s",
            "--store",
            dest="store",
            default=False,
            help="Store the created config in the config file",
            action=argparse.BooleanOptionalAction,
        )
        parser.add_argument(
            "--module_paths",
            dest="module_paths",
            nargs="+",
            default=[],
            help="additional paths to search for modules",
            action=UniqueAppendAction,
        )

        self.basic_parser = parser
        return parser

    def check_steps(self, config):
        for module_type in MODULE_TYPES:
            if not config["steps"].get(f"{module_type}s", []):
                if (module_type == "feeder" or module_type == "formatter") and config["steps"].get(f"{module_type}"):
                    raise SetupError(
                        f"It appears you have '{module_type}' set under 'steps' in your configuration file, but as of version 0.13.0 of Auto Archiver, you must use '{module_type}s'. Change this in your configuration file and try again. \
Here's how that would look: \n\nsteps:\n  {module_type}s:\n  - [your_{module_type}_name_here]\n  {'extractors:...' if module_type == 'feeder' else '...'}\n"
                    )
                if module_type == "extractor" and config["steps"].get("archivers"):
                    raise SetupError(
                        "As of version 0.13.0 of Auto Archiver, the 'archivers' step name has been changed to 'extractors'. Change this in your configuration file and try again. \
Here's how that would look: \n\nsteps:\n  extractors:\n  - [your_extractor_name_here]\n  enrichers:...\n"
                    )
                raise SetupError(
                    f"No {module_type}s were configured. Make sure to set at least one {module_type} in your configuration file or on the command line (using --{module_type}s)"
                )

    def setup_complete_parser(self, basic_config: dict, yaml_config: dict, unused_args: list[str]) -> None:
        # modules parser to get the overridden 'steps' values
        modules_parser = argparse.ArgumentParser(
            add_help=False,
        )
        self.add_modules_args(modules_parser)
        cli_modules, unused_args = modules_parser.parse_known_args(unused_args)
        for module_type in MODULE_TYPES:
            yaml_config["steps"][f"{module_type}s"] = getattr(cli_modules, f"{module_type}s", []) or yaml_config[
                "steps"
            ].get(f"{module_type}s", [])

        parser = DefaultValidatingParser(
            add_help=False,
        )
        self.add_additional_args(parser)

        # merge command line module args (--feeders, --enrichers etc.) and add them to the config

        # check what mode we're in
        # if we have a config file, use that to decide which modules to load
        # if simple, we'll load just the modules that has requires_setup = False
        # if full, we'll load all modules
        # TODO: BUG** - basic_config won't have steps in it, since these args aren't added to 'basic_parser'
        # but should we add them? Or should we just add them to the 'complete' parser?

        if is_valid_config(yaml_config):
            self.check_steps(yaml_config)
            # only load the modules enabled in config
            # TODO: if some steps are empty (e.g. 'feeders' is empty), should we default to the 'simple' ones? Or only if they are ALL empty?
            enabled_modules = []
            # first loads the modules from the config file, then from the command line
            for module_type in MODULE_TYPES:
                enabled_modules.extend(yaml_config["steps"].get(f"{module_type}s", []))

            # clear out duplicates, but keep the order
            enabled_modules = list(dict.fromkeys(enabled_modules))
            avail_modules = self.module_factory.available_modules(
                limit_to_modules=enabled_modules, suppress_warnings=True
            )
            self.add_individual_module_args(avail_modules, parser)
        elif basic_config.mode == "simple":
            simple_modules = [module for module in self.module_factory.available_modules() if not module.requires_setup]
            self.add_individual_module_args(simple_modules, parser)

            # add them to the config
            for module in simple_modules:
                for module_type in module.type:
                    yaml_config["steps"].setdefault(f"{module_type}s", []).append(module.name)
        else:
            # load all modules, they're not using the 'simple' mode
            all_modules = self.module_factory.available_modules()
            # add all the modules to the steps
            for module in all_modules:
                for module_type in module.type:
                    yaml_config["steps"].setdefault(f"{module_type}s", []).append(module.name)

            self.add_individual_module_args(all_modules, parser)

        parser.set_defaults(**to_dot_notation(yaml_config))

        # reload the parser with the new arguments, now that we have them
        parsed, unknown = parser.parse_known_args(unused_args)
        # merge the new config with the old one
        config = merge_dicts(vars(parsed), yaml_config)

        # set up the authentication dict as needed
        config = self.setup_authentication(config)

        # clean out args from the base_parser that we don't want in the config
        for key in vars(basic_config):
            config.pop(key, None)

        # setup the logging
        self.setup_logging(config)

        if unknown:
            logger.warning(f"Ignoring unknown/unused arguments: {unknown}\nPerhaps you don't have this module enabled?")

        if (config != yaml_config and basic_config.store) or not os.path.isfile(basic_config.config_file):
            logger.info(f"Storing configuration file to {basic_config.config_file}")
            store_yaml(config, basic_config.config_file)

        return config

    def add_modules_args(self, parser: argparse.ArgumentParser = None):
        if not parser:
            parser = self.parser

        # Module loading from the command line
        for module_type in MODULE_TYPES:
            parser.add_argument(
                f"--{module_type}s",
                dest=f"{module_type}s",
                nargs="+",
                help=f"the {module_type}s to use",
                default=[],
                action=UniqueAppendAction,
            )

    def add_additional_args(self, parser: argparse.ArgumentParser = None):
        if not parser:
            parser = self.parser

        parser.add_argument(
            "--authentication",
            dest="authentication",
            help="A dictionary of sites and their authentication methods \
                                                                            (token, username etc.) that extractors can use to log into \
                                                                            a website. If passing this on the command line, use a JSON string. \
                                                                            You may also pass a path to a valid JSON/YAML file which will be parsed.",
            default={},
            nargs="?",
            action=AuthenticationJsonParseAction,
        )

        # logging arguments
        parser.add_argument(
            "--logging.level",
            action="store",
            dest="logging.level",
            choices=["INFO", "DEBUG", "ERROR", "WARNING"],
            help="the logging level to use for the standard output and file logging",
            default="INFO",
            type=str.upper,
        )
        parser.add_argument(
            "--logging.file", action="store", dest="logging.file", help="the logging file to write to", default=None
        )
        parser.add_argument(
            "--logging.rotation",
            action="store",
            dest="logging.rotation",
            help="the logging rotation to use",
            default=None,
        )

        parser.add_argument(
            "--logging.each_level_in_separate_file",
            action="store",
            dest="logging.each_level_in_separate_file",
            help="if set, writes each logging level to a separate file (ignores --logging.level), you must also set --logging.file. Each level will have a dedicate logs file matching your <file>.debug, <file>.info, etc.",
            default=False,
        )

    def add_individual_module_args(
        self, modules: list[LazyBaseModule] = None, parser: argparse.ArgumentParser = None
    ) -> None:
        if not modules:
            modules = self.module_factory.available_modules()

        for module in modules:
            if module.name == "cli_feeder":
                # special case. For the CLI feeder, allow passing URLs directly on the command line without setting --cli_feeder.urls=
                parser.add_argument(
                    "urls",
                    nargs="*",
                    default=[],
                    help="URL(s) to archive, either a single URL or a list of urls, should not come from config.yaml",
                )
                continue

            if not module.configs:
                # this module has no configs, don't show anything in the help
                # (TODO: do we want to show something about this module though, like a description?)
                continue

            group = parser.add_argument_group(module.display_name or module.name, f"{module.description[:100]}...")

            for name, kwargs in module.configs.items():
                if not kwargs.get("metavar", None):
                    # make a nicer metavar, metavar is what's used in the help, e.g. --cli_feeder.urls [METAVAR]
                    kwargs["metavar"] = name.upper()

                if kwargs.get("required", False):
                    # required args shouldn't have a 'default' value, remove it
                    kwargs.pop("default", None)

                kwargs.pop("cli_set", None)
                should_store = kwargs.pop("should_store", False)
                kwargs["dest"] = f"{module.name}.{kwargs.pop('dest', name)}"
                try:
                    kwargs["type"] = getattr(validators, kwargs.get("type", "__invalid__"))
                except AttributeError:
                    kwargs["type"] = __builtins__.get(kwargs.get("type"), str)
                arg = group.add_argument(f"--{module.name}.{name}", **kwargs)
                arg.should_store = should_store

    def show_help(self, basic_config: dict):
        # for the help message, we want to load manifests from *all* possible modules and show their help/settings
        # add configs as arg parser arguments

        self.add_modules_args(self.basic_parser)
        self.add_additional_args(self.basic_parser)
        self.add_individual_module_args(parser=self.basic_parser)
        self.basic_parser.print_help()
        self.basic_parser.exit()

    def setup_logging(self, config):
        logging_config = config["logging"]

        if logging_config.get("enabled", True) is False:
            # disabled logging settings, they're set on a higher level
            logger.disable("auto_archiver")
            return

        # setup loguru logging
        try:
            logger.remove(0)  # remove the default logger
        except ValueError:
            pass

        # add other logging info
        if self.logger_id is None:  # note - need direct comparison to None since need to consider falsy value 0
            use_level = logging_config["level"]
            self.logger_id = logger.add(
                sys.stderr,
                level=use_level,
                catch=True,
                format="<level>{extra[serialized]}</level>"
                if logging_config.get("format", "").lower() == "json"
                else format_for_human_readable_console(),
            )

            rotation = logging_config["rotation"]
            log_file = logging_config["file"]

            if logging_config.get("each_level_in_separate_file"):
                assert logging_config["file"], (
                    "You must set --logging.file if you want to use --logging.each_level_in_separate_file"
                )
                for i, level in enumerate(["DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR"], start=1):
                    logger.add(
                        f"{log_file}.{i}_{level.lower()}",
                        filter=lambda rec, lvl=level: rec["level"].name == lvl,
                        rotation=rotation,
                        format="{extra[serialized]}",
                    )
            elif log_file:
                logger.add(log_file, rotation=rotation, level=use_level, format="{extra[serialized]}")

    def install_modules(self, modules_by_type):
        """
        Traverses all modules in 'steps' and loads them into the orchestrator, storing them in the
        orchestrator's attributes (self.feeders, self.extractors etc.). If no modules of a certain type
        are loaded, the program will exit with an error message.
        """

        invalid_modules = []
        for module_type in MODULE_TYPES:
            step_items = []
            modules_to_load = modules_by_type[f"{module_type}s"]
            if not modules_to_load:
                raise SetupError(
                    f"No {module_type}s were configured. Make sure to set at least one {module_type} in your configuration file or on the command line (using --{module_type}s)"
                )

            def check_steps_ok():
                if not len(step_items):
                    if len(modules_to_load):
                        logger.error(
                            f"Unable to load any {module_type}s. Tried the following, but none were available: {modules_to_load}"
                        )
                    raise SetupError(
                        f"NO {module_type.upper()}S LOADED. Please check your configuration and try again."
                    )

                if (module_type == "feeder" or module_type == "formatter") and len(step_items) > 1:
                    raise SetupError(
                        f"Only one {module_type} is allowed, found {len(step_items)} {module_type}s. Please remove one of the following from your configuration file: {modules_to_load}"
                    )

            for module in modules_to_load:
                if module in invalid_modules:
                    continue

                # check to make sure that we're trying to load it as the correct type - i.e. make sure the user hasn't put it under the wrong 'step'
                lazy_module: LazyBaseModule = self.module_factory.get_module_lazy(module)
                if module_type not in lazy_module.type:
                    types = ",".join(f"'{t}'" for t in lazy_module.type)
                    raise SetupError(
                        f"Configuration Error: Module '{module}' is not a {module_type}, but has the types: {types}. Please check you set this module up under the right step in your orchestration file."
                    )

                loaded_module = None
                try:
                    loaded_module: BaseModule = lazy_module.load(self.config)
                except (KeyboardInterrupt, Exception) as e:
                    if not isinstance(e, KeyboardInterrupt) and not isinstance(e, SetupError):
                        logger.error(f"Error during setup of modules: {e}\n{traceback.format_exc()}")

                    # access the _instance here because loaded_module may not return if there's an error
                    if lazy_module._instance and module_type == "extractor":
                        lazy_module._instance.cleanup()
                    raise e

                if not loaded_module:
                    invalid_modules.append(module)
                    continue
                if loaded_module:
                    step_items.append(loaded_module)

            check_steps_ok()
            setattr(self, f"{module_type}s", step_items)

    def load_config(self, config_file: str) -> dict:
        if not os.path.exists(config_file) and config_file != DEFAULT_CONFIG_FILE:
            logger.error(
                f"The configuration file {config_file} was  not found. Make sure the file exists and try again, or run without the --config file to use the default settings."
            )
            raise FileNotFoundError(f"Configuration file {config_file} not found")

        return read_yaml(config_file)

    def setup_config(self, args: list) -> dict:
        """
        Sets up the configuration file, merging the default config with the user's config

        This function should only ever be run once.
        """

        self.setup_basic_parser()

        # parse the known arguments for now (basically, we want the config file)
        basic_config, unused_args = self.basic_parser.parse_known_args(args)

        # setup any custom module paths, so they'll show in the help and for arg parsing
        self.module_factory.setup_paths(basic_config.module_paths)

        # if help flag was called, then show the help
        if basic_config.help:
            self.show_help(basic_config)
        # merge command line --feeder etc. args with what's in the yaml config
        yaml_config = self.load_config(basic_config.config_file)

        return self.setup_complete_parser(basic_config, yaml_config, unused_args)

    def check_for_updates(self):
        response = requests.get("https://pypi.org/pypi/auto-archiver/json").json()
        latest_version = version.parse(response["info"]["version"])
        current_version = version.parse(__version__)
        # check version compared to current version
        if latest_version > current_version:
            if os.environ.get("RUNNING_IN_DOCKER"):
                update_cmd = "`docker pull bellingcat/auto-archiver:latest`"
            else:
                update_cmd = "`pip install --upgrade auto-archiver`"
            logger.warning(
                f"\n********* IMPORTANT: UPDATE AVAILABLE ********\nA new version of auto-archiver is available (v{latest_version}, you have v{current_version})\nMake sure to update to the latest version using: {update_cmd}\n"
            )

    def setup(self, args: list):
        """
        Function to configure all setup of the orchestrator: setup configs and load modules.

        This method should only ever be called once
        """

        self.check_for_updates()

        if self.setup_finished:
            logger.warning(
                "The `setup_config()` function should only ever be run once. \
                           If you need to re-run the setup, please re-instantiate a new instance of the orchestrator. \
                           For code implementatations, you should call .setup_config() once then you may call .feed() \
                           multiple times to archive multiple URLs."
            )
            return

        self.setup_basic_parser()
        self.config = self.setup_config(args)

        logger.info(f"======== Welcome to the AUTO ARCHIVER ({__version__}) ==========")
        self.install_modules(self.config["steps"])

        # log out the modules that were loaded
        for module_type in MODULE_TYPES:
            logger.info(
                f"{module_type.upper()}S: " + ", ".join(m.display_name for m in getattr(self, f"{module_type}s"))
            )

        self.setup_finished = True

    def _command_line_run(self, args: list) -> Generator[Metadata]:
        """
        This is the main entry point for the orchestrator, when run from the command line.

        :param args: list of arguments to pass to the orchestrator - these are the command line args

        You should not call this method from code implementations.

        This method sets up the configuration, loads the modules, and runs the feed.
        If you wish to make code invocations yourself, you should use the 'setup' and 'feed' methods separately.
        To test configurations, without loading any modules you can also first call 'setup_configs'
        """
        try:
            self.setup(args)
            return self.feed()
        except Exception as e:
            logger.error(f"{e}: {traceback.format_exc()}")
            exit(1)

    def cleanup(self) -> None:
        logger.info("Cleaning up")
        for e in self.extractors:
            e.cleanup()

    def feed(self) -> Generator[Metadata]:
        url_count = 0
        for feeder in self.feeders:
            for item in feeder:
                with logger.contextualize(url=item.get_url(), trace=random_str(12)):
                    logger.info("Started processing")
                    yield self.feed_item(item)
                    url_count += 1

        logger.info(f"Processed {url_count} URL(s)")
        self.cleanup()

    def feed_item(self, item: Metadata) -> Metadata:
        """
        Takes one item (URL) to archive and calls self.archive, additionally:
            - catches keyboard interruptions to do a clean exit
            - catches any unexpected error, logs it, and does a clean exit
        """
        tmp_dir: TemporaryDirectory = None
        try:
            tmp_dir = TemporaryDirectory(dir="./")
            # set tmp_dir on all modules
            for m in self.all_modules:
                m.tmp_dir = tmp_dir.name
            return self.archive(item)
        except KeyboardInterrupt:
            # catches keyboard interruptions to do a clean exit
            logger.warning("Caught interrupt")
            for d in self.databases:
                d.aborted(item)
            self.cleanup()
            exit()
        except Exception as e:
            logger.error(f"Got unexpected error: {e}\n{traceback.format_exc()}")
            for d in self.databases:
                if isinstance(e, AssertionError):
                    d.failed(item, str(e))
                else:
                    d.failed(item, reason="unexpected error")
        finally:
            if tmp_dir:
                # remove the tmp_dir from all modules
                for m in self.all_modules:
                    m.tmp_dir = None
                tmp_dir.cleanup()

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
        try:
            check_url_or_raise(original_url)
        except ValueError as e:
            logger.error(f"Error archiving: {e}")
            raise e

        # 1 - sanitize - each archiver is responsible for cleaning/expanding its own URLs
        url = clean(original_url)
        for a in self.extractors:
            url = a.sanitize_url(url)

        result.set_url(url)
        if original_url != url:
            logger.debug(f"Sanitized URL to {url}")
            result.set("original_url", original_url)

        # 2 - notify start to DBs, propagate already archived if feature enabled in DBs
        cached_result = None
        for d in self.databases:
            d.started(result)
            if local_result := d.fetch(result):
                cached_result = (cached_result or Metadata()).merge(local_result).merge(result)
        if cached_result:
            logger.debug("Found previously archived entry")
            for d in self.databases:
                try:
                    d.done(cached_result, cached=True)
                except Exception as e:
                    logger.error(f"Database {d.name}: {e}: {traceback.format_exc()}")
            return cached_result

        # 3 - call extractors until one succeeds
        for a in self.extractors:
            logger.info(f"Trying extractor {a.name}")
            try:
                result.merge(a.download(result))
                if result.is_success():
                    break
            except Exception as e:
                logger.error(f"Extractor {a.name}: {e}: {traceback.format_exc()}")

        # 4 - call enrichers to work with archived content
        for e in self.enrichers:
            try:
                e.enrich(result)
            except Exception as exc:
                logger.error(f"Enricher {e.name}: {exc}: {traceback.format_exc()}")

        # 5 - store all downloaded/generated media
        result.store(storages=self.storages)

        # 6 - format and store formatted if needed
        final_media: Media
        if final_media := self.formatters[0].format(result):
            final_media.store(url=url, metadata=result, storages=self.storages)
            result.set_final_media(final_media)

        if result.is_empty():
            result.status = "nothing archived"

        # signal completion to databases and archivers
        for d in self.databases:
            try:
                d.done(result)
            except Exception as e:
                logger.error(f"Database {d.name}: {e}: {traceback.format_exc()}")

        return result

    def setup_authentication(self, config: dict) -> dict:
        """
        Setup authentication for all modules that require it

        Split up strings into multiple sites if they are comma separated
        """

        authentication = config.get("authentication", {})

        # extract out concatenated sites
        for key, val in copy(authentication).items():
            if "," in key:
                for site in key.split(","):
                    site = site.strip()
                    authentication[site] = val
                del authentication[key]

        config["authentication"] = authentication
        return config

    # Helper Properties

    @property
    def all_modules(self) -> List[Type[BaseModule]]:
        return self.feeders + self.extractors + self.enrichers + self.databases + self.storages + self.formatters
