""" This module contains the storage classes for the auto-archiver.

"""
from .storage import Storage
from .s3 import S3Storage
from .local import LocalStorage
from .gd import GDriveStorage
from .atlos import AtlosStorage