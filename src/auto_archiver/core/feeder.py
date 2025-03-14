"""
The feeder base module defines the interface for implementing feeders in the media archiving framework.
"""

from __future__ import annotations
from abc import abstractmethod
from auto_archiver.core import Metadata
from auto_archiver.core import BaseModule


class Feeder(BaseModule):
    """
    Base class for implementing feeders in the media archiving framework.

    Subclasses must implement the `__iter__` method to define platform-specific behavior.
    """

    @abstractmethod
    def __iter__(self) -> Metadata:
        """
        Returns an iterator (use `yield`) over the items to be archived.

        These should be instances of Metadata, typically created with Metadata().set_url(url).
        """
        return None
