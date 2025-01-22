"""
The Config class initializes and parses configurations for all other steps.
It supports CLI argument parsing, loading from YAML file, and overrides to allow
flexible setup in various environments.

"""

import argparse
import yaml
from dataclasses import dataclass, field
from collections import OrderedDict

from .loader import MODULE_TYPES

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

EMPTY_CONFIG = {
    "steps": dict((f"{module_type}s", []) for module_type in MODULE_TYPES)
}
class LoadFromFile (argparse.Action):
    def __call__ (self, parser, namespace, values, option_string = None):
        with values as f:
            # parse arguments in the file and store them in the target namespace
            parser.parse_args(f.read().split(), namespace)

def to_dot_notation(yaml_conf: str) -> argparse.ArgumentParser:
    dotdict = {}

    def process_subdict(subdict, prefix=""):
        for key, value in subdict.items():
            if type(value) == dict:
                process_subdict(value, f"{prefix}{key}.")
            else:
                dotdict[f"{prefix}{key}"] = value

    process_subdict(yaml_conf)
    return dotdict

def merge_dicts(dotdict, yaml_dict):
    def process_subdict(subdict, prefix=""):
        for key, value in subdict.items():
            if "." in key:
                keys = key.split(".")
                subdict = yaml_dict
                for k in keys[:-1]:
                    subdict = subdict.setdefault(k, {})
                subdict[keys[-1]] = value
            else:
                yaml_dict[key] = value

    process_subdict(dotdict)
    return yaml_dict

def read_yaml(yaml_filename: str) -> dict:

    try:
        with open(yaml_filename, "r", encoding="utf-8") as inf:
            config = yaml.safe_load(inf)
    except FileNotFoundError:
        config = EMPTY_CONFIG

    return config

def store_yaml(config: dict, yaml_filename: str):
    with open(yaml_filename, "w", encoding="utf-8") as outf:
        yaml.dump(config, outf, default_flow_style=False)