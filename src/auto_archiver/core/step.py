"""
Defines the Step abstract base class, which acts as a blueprint for steps in the archiving pipeline
by handling user configuration, validating the steps properties, and implementing dynamic instantiation.

"""

from __future__ import annotations
from dataclasses import dataclass
from inspect import ClassFoundException
from typing import Type
from abc import ABC


@dataclass
class Step(ABC):
    name: str = None

    def __init__(self, config: dict) -> None:
        # Initialises each step by reading the relevant entries
        # reads the configs into object properties
        # self.config = config[self.name]
        for k, v in config.get(self.name, {}).items():
            self.__setattr__(k, v)

    @staticmethod
    def configs() -> dict: return {}

    def init(name: str, config: dict, child: Type[Step]) -> Step:
        """
        Attempts to instantiate a subclass of the provided `child` type
        matching the given `name`.
        Raises ClassFoundException if no matching subclass is found.
        TODO: cannot find subclasses of child.subclasses
        """
        for sub in child.__subclasses__():
            if sub.name == name:
                return sub(config)
        raise ClassFoundException(f"Unable to initialize STEP with {name=}, check your configuration file/step names, and make sure you made the step discoverable by putting it into __init__.py")

    def assert_valid_string(self, prop: str) -> None:
        """
        Receives a property name and ensures it exists and is a valid non-empty string,
        raising an AssertionError if not.
        TODO: replace assertions with custom exceptions.
        """
        assert hasattr(self, prop), f"property {prop} not found"
        s = getattr(self, prop)
        assert s is not None and type(s) == str and len(s) > 0, f"invalid property {prop} value '{s}', it should be a valid string"
