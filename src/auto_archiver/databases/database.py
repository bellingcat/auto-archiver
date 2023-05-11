from __future__ import annotations
from dataclasses import dataclass
from abc import abstractmethod, ABC
from typing import Union

from ..core import Metadata, Step


@dataclass
class Database(Step, ABC):
    name = "database"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    def init(name: str, config: dict) -> Database:
        # only for typing...
        return Step.init(name, config, Database)

    def started(self, item: Metadata) -> None:
        """signals the DB that the given item archival has started"""
        pass

    def failed(self, item: Metadata) -> None:
        """update DB accordingly for failure"""
        pass

    def aborted(self, item: Metadata) -> None:
        """abort notification if user cancelled after start"""
        pass

    # @abstractmethod
    def fetch(self, item: Metadata) -> Union[Metadata, bool]:
        """check if the given item has been archived already"""
        return False

    @abstractmethod
    def done(self, item: Metadata) -> None:
        """archival result ready - should be saved to DB"""
        pass
