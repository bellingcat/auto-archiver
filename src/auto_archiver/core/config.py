"""
The Config class initializes and parses configurations for all other steps.
It supports CLI argument parsing, loading from YAML file, and overrides to allow
flexible setup in various environments.

"""

import argparse
from ruamel.yaml import YAML, CommentedMap, add_representer

from copy import deepcopy
from .loader import MODULE_TYPES

from typing import Any, List, Type

#     configurable_parents = [
#         Feeder,
#         Enricher,
#         Extractor,
#         Database,
#         Storage,
#         Formatter
#         # Util
#     ]
#     feeder: Feeder
#     formatter: Formatter
#     extractors: List[Extractor] = field(default_factory=[])
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

EMPTY_CONFIG = CommentedMap(**{
    "steps": dict((f"{module_type}s", []) for module_type in MODULE_TYPES)
})

def to_dot_notation(yaml_conf: CommentedMap | dict) -> argparse.ArgumentParser:
    dotdict = {}

    def process_subdict(subdict, prefix=""):
        for key, value in subdict.items():
            if is_dict_type(value):
                process_subdict(value, f"{prefix}{key}.")
            else:
                dotdict[f"{prefix}{key}"] = value

    process_subdict(yaml_conf)
    return dotdict

def from_dot_notation(dotdict: dict) -> dict:
    normal_dict = {}

    def add_part(key, value, current_dict):
        if "." in key:
            key_parts = key.split(".")
            current_dict.setdefault(key_parts[0], {})
            add_part(".".join(key_parts[1:]), value, current_dict[key_parts[0]])
        else:
            current_dict[key] = value

    for key, value in dotdict.items():
        add_part(key, value, normal_dict)

    return normal_dict


def is_list_type(value):
    return isinstance(value, list) or isinstance(value, tuple) or isinstance(value, set)

def is_dict_type(value):
    return isinstance(value, dict) or isinstance(value, CommentedMap)

def merge_dicts(dotdict: dict, yaml_dict: CommentedMap) -> CommentedMap:
    yaml_dict: CommentedMap = deepcopy(yaml_dict)

    # first deal with lists, since 'update' replaces lists from a in b, but we want to extend
    def update_dict(subdict, yaml_subdict):
        for key, value in subdict.items():
            if not yaml_subdict.get(key):
                yaml_subdict[key] = value
                continue

            if is_dict_type(value):
                update_dict(value, yaml_subdict[key])
            elif is_list_type(value):
                yaml_subdict[key].extend(s for s in value if s not in yaml_subdict[key])
            else:
                yaml_subdict[key] = value

    update_dict(from_dot_notation(dotdict), yaml_dict)

    return yaml_dict

yaml = YAML()

def read_yaml(yaml_filename: str) -> CommentedMap:
    config = None
    try:
        with open(yaml_filename, "r", encoding="utf-8") as inf:
            config = yaml.load(inf)
    except FileNotFoundError:
        pass

    if not config:
        config = EMPTY_CONFIG
    
    return config

def store_yaml(config: CommentedMap, yaml_filename: str):
    with open(yaml_filename, "w", encoding="utf-8") as outf:
        yaml.dump(config, outf)