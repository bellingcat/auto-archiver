"""Version information for the auto_archiver package.
TODO: This is a placeholder to replicate previous versioning.

"""

from importlib.metadata import version as get_version

VERSION_SHORT = get_version("auto_archiver")

# This is mainly for nightly builds which have the suffix ".dev$DATE". See
# https://semver.org/#is-v123-a-semantic-version for the semantics.
_SUFFIX = ""
__version__ = f"{VERSION_SHORT}{_SUFFIX}"
