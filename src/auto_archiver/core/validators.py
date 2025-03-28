# used as validators for config values. Should raise an exception if the value is invalid.
from pathlib import Path
import argparse
import json


def positive_number(value):
    if value < 0:
        raise argparse.ArgumentTypeError(f"{value} is not a positive number")
    return value


def valid_file(value):
    if not Path(value).is_file():
        raise argparse.ArgumentTypeError(f"File '{value}' does not exist.")
    return value


def json_loader(cli_val):
    return json.loads(cli_val)
