"""
The Config class initializes and parses configurations for all other steps.
It supports CLI argument parsing, loading from YAML file, and overrides to allow
flexible setup in various environments.

"""
import argparse
from configparser import ConfigParser
from dataclasses import dataclass, field


#     configurable_parents = [
#         Feeder,
#         Enricher,
#         Archiver,
#         Database,
#         Storage,
#         Formatter
#         # Util
#     ]
#     feeder: Feeder
#     formatter: Formatter
#     archivers: List[Archiver] = field(default_factory=[])
#     enrichers: List[Enricher] = field(default_factory=[])
#     storages: List[Storage] = field(default_factory=[])
#     databases: List[Database] = field(default_factory=[])

#     def __init__(self) -> None:
#         self.defaults = {}
#         self.cli_ops = {}
#         self.config = {}

    # def parse(self, use_cli=True, yaml_config_filename: str = None, overwrite_configs: str = {}):
    #     """
    #     if yaml_config_filename is provided, the --config argument is ignored, 
    #     useful for library usage when the config values are preloaded
    #     overwrite_configs is a dict that overwrites the yaml file contents
    #     """
        # # 1. parse CLI values
        # if use_cli:
        #     parser = argparse.ArgumentParser(
        #         # prog = "auto-archiver",
        #         description="Auto Archiver is a CLI tool to archive media/metadata from online URLs; it can read URLs from many sources (Google Sheets, Command Line, ...); and write results to many destinations too (CSV, Google Sheets, MongoDB, ...)!",
        #         epilog="Check the code at https://github.com/bellingcat/auto-archiver"
        #     )

        #     parser.add_argument('--config', action='store', dest='config', help='the filename of the YAML configuration file (defaults to \'config.yaml\')', default='orchestration.yaml')
        #     parser.add_argument('--version', action='version', version=__version__)


class LoadFromFile (argparse.Action):
    def __call__ (self, parser, namespace, values, option_string = None):
        with values as f:
            # parse arguments in the file and store them in the target namespace
            parser.parse_args(f.read().split(), namespace)

def read_config(config_filename: str) -> dict:
    config = ConfigParser()
    config.read(config_filename)
    # setup basic format
    if 'STEPS' not in config.sections():
        config.add_section("STEPS")
    return config

def store_config(config: ConfigParser, config_filename: str):
    with open(config_filename, "w", encoding="utf-8") as outf:
        config.write(outf)