# used as validators for config values. Should raise an exception if the value is invalid.
from pathlib import Path
import argparse

def example_validator(value):
    if "example" not in value:
        raise argparse.ArgumentTypeError(f"{value} is not a valid value for this argument")
    return value

def positive_number(value):
    if value < 0:
        raise argparse.ArgumentTypeError(f"{value} is not a positive number")
    return value


def valid_file(value):
    if not Path(value).is_file():
        raise argparse.ArgumentTypeError(f"File '{value}' does not exist.")
    return value