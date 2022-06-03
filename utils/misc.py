
import os, requests
from loguru import logger


def mkdir_if_not_exists(folder):
    if not os.path.exists(folder):
        os.mkdir(folder)


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
