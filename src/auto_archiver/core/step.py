"""
Defines the Step abstract base class, which acts as a blueprint for steps in the archiving pipeline
by handling user configuration, validating the steps properties, and implementing dynamic instantiation.

"""

from __future__ import annotations

class Step:
    # TODO: try and get this name from the manifest, so we don't have to set it twice
    name: str