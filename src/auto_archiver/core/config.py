"""
The Config class initializes and parses configurations for all other steps.
It supports CLI argument parsing, loading from YAML file, and overrides to allow
flexible setup in various environments.

"""

import argparse
from ruamel.yaml import YAML, CommentedMap, add_representer

from loguru import logger

from copy import deepcopy
from .module import BaseModule

from typing import Any, List, Type, Tuple

_yaml: YAML = YAML()

EMPTY_CONFIG = _yaml.load("""
# Auto Archiver Configuration
# Steps are the modules that will be run in the order they are defined

steps:""" + "".join([f"\n   {module}s: []" for module in BaseModule.MODULE_TYPES]) + \
"""

# Global configuration

# Authentication
# a dictionary of authentication information that can be used by extractors to login to website. 
# you can use a comma separated list for multiple domains on the same line (common usecase: x.com,twitter.com)
# Common login 'types' are username/password, cookie, api key/token.
# There are two special keys for using cookies, they are: cookies_file and cookies_from_browser. 
# Some Examples:
# facebook.com:
#   username: "my_username"
#   password: "my_password"
# or for a site that uses an API key:
# twitter.com,x.com:
#   api_key
#   api_secret
# youtube.com:
#   cookie: "login_cookie=value ; other_cookie=123" # multiple 'key=value' pairs should be separated by ;

authentication: {}

# These are the global configurations that are used by the modules

logging:
  level: INFO

""")
# note: 'logging' is explicitly added above in order to better format the config file

class DefaultValidatingParser(argparse.ArgumentParser):

    def error(self, message):
        """
        Override of error to format a nicer looking error message using logger
        """
        logger.error("Problem with configuration file (tip: use --help to see the available options):")
        logger.error(message)
        self.exit(2)

    def parse_known_args(self, args=None, namespace=None):
        """
        Override of parse_known_args to also check the 'defaults' values - which are passed in from the config file
        """
        for action in self._actions:
            if not namespace or action.dest not in namespace:
                # for actions that are required and already have a default value, remove the 'required' check
                if action.required and action.default is not None:
                    action.required = False

                if action.default is not None:
                    try:
                        self._check_value(action, action.default)
                    except argparse.ArgumentError as e:
                        logger.error(f"You have an invalid setting in your configuration file ({action.dest}):")
                        logger.error(e)
                        exit()

        return super().parse_known_args(args, namespace)


def to_dot_notation(yaml_conf: CommentedMap | dict) -> dict:
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

def read_yaml(yaml_filename: str) -> CommentedMap:
    config = None
    try:
        with open(yaml_filename, "r", encoding="utf-8") as inf:
            config = _yaml.load(inf)
    except FileNotFoundError:
        pass

    if not config:
        config = EMPTY_CONFIG
    
    return config

# TODO: make this tidier/find a way to notify of which keys should not be stored


def store_yaml(config: CommentedMap, yaml_filename: str) -> None:
    config_to_save = deepcopy(config)

    config_to_save.pop('urls', None)
    with open(yaml_filename, "w", encoding="utf-8") as outf:
        _yaml.dump(config_to_save, outf)