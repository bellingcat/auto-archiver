import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from dateutil.parser import parse as parse_dt

import requests
from loguru import logger


def mkdir_if_not_exists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)


def expand_url(url):
    # expand short URL links
    if "https://t.co/" in url:
        try:
            r = requests.get(url)
            logger.debug(f"Expanded url {url} to {r.url}")
            return r.url
        except Exception:
            logger.error(f"Failed to expand url {url}")
    return url


def getattr_or(o: object, prop: str, default=None):
    try:
        res = getattr(o, prop)
        if res is None:
            raise
        return res
    except Exception:
        return default


class DateTimeEncoder(json.JSONEncoder):
    # to allow json.dump with datetimes do json.dumps(obj, cls=DateTimeEncoder)
    def default(self, o):
        if isinstance(o, datetime):
            return str(o)  # with timezone
        return json.JSONEncoder.default(self, o)


def dump_payload(p):
    return json.dumps(p, ensure_ascii=False, indent=4, cls=DateTimeEncoder)


def update_nested_dict(dictionary, update_dict):
    # takes 2 dicts and overwrites the first with the second only on the changed values
    for key, value in update_dict.items():
        if key in dictionary and isinstance(value, dict) and isinstance(dictionary[key], dict):
            update_nested_dict(dictionary[key], value)
        else:
            dictionary[key] = value


def random_str(length: int = 32) -> str:
    assert length <= 32, "length must be less than 32 as UUID4 is used"
    return str(uuid.uuid4()).replace("-", "")[:length]


def calculate_file_hash(filename: str, hash_algo=hashlib.sha256, chunksize: int = 16000000) -> str:
    hash = hash_algo()
    with open(filename, "rb") as f:
        while True:
            buf = f.read(chunksize)
            if not buf:
                break
            hash.update(buf)
    return hash.hexdigest()


def get_datetime_from_str(dt_str: str, fmt: str | None = None, dayfirst=True) -> datetime | None:
    """parse a datetime string with option of passing a specific format

    Args:
        dt_str: the datetime string to parse
        fmt: the python date format of the datetime string, if None, dateutil.parser.parse is used
        dayfirst: Use this to signify between date formats which put the day first, vs the month first:
                    e.g. DD/MM/YYYY vs MM/DD/YYYY
    """
    try:
        return datetime.strptime(dt_str, fmt) if fmt else parse_dt(dt_str, dayfirst=dayfirst)
    except ValueError as e:
        logger.error(f"Unable to parse datestring {dt_str}: {e}")
        return None


def get_timestamp(ts, utc=True, iso=True, dayfirst=True) -> str | datetime | None:
    """Consistent parsing of timestamps.
    Args:
         If utc=True, the timezone is set to UTC,
         if iso=True, the output is an iso string
         Use dayfirst to signify between date formats which put the date vs month first:
         e.g. DD/MM/YYYY vs MM/DD/YYYY
    """
    if not ts:
        return
    try:
        if isinstance(ts, str):
            ts = parse_dt(ts, dayfirst=dayfirst)
        if isinstance(ts, (int, float)):
            ts = datetime.fromtimestamp(ts)
        if utc:
            ts = ts.replace(tzinfo=timezone.utc)
        if iso:
            return ts.isoformat()
        return ts
    except Exception as e:
        logger.error(f"Unable to parse timestamp {ts}: {e}")
        return None


def get_current_timestamp() -> str:
    return get_timestamp(datetime.now())
