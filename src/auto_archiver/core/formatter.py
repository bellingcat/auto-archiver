"""
Base module for formatters – modular components that format metadata into media objects for storage.

The most commonly used formatter is the HTML formatter, which takes metadata and formats it into an HTML file for storage.
"""

from __future__ import annotations
from abc import abstractmethod
from auto_archiver.core import Metadata, Media, BaseModule


class Formatter(BaseModule):
    """
    Base class for implementing formatters in the media archiving framework.

    Subclasses must implement the `format` method to define their behavior.
    """

    @abstractmethod
    def format(self, item: Metadata) -> Media:
        """
        Formats a Metadata object into a user-viewable format (e.g. HTML) and stores it if needed.
        """
        return None
