
import os, json, requests
from datetime import datetime
from loguru import logger


def mkdir_if_not_exists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)


def expand_url(url):
    # expand short URL links
    if 'https://t.co/' in url:
        try:
            r = requests.get(url)
            logger.debug(f'Expanded url {url} to {r.url}')
            return r.url
        except:
            logger.error(f'Failed to expand url {url}')
    return url


def getattr_or(o: object, prop: str, default=None):
    try:
        res = getattr(o, prop)
        if res is None: raise
        return res
    except:
        return default

