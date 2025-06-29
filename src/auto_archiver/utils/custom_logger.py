from loguru import logger
import json


def extract_location(record, short=False):
    """Extracts the file name, function name, and line number from the log record."""
    if short:
        return f"{record['file'].name}:{record['line']}"
    return f"{record['file'].name}:{record['function']}:{record['line']}"


def extract_log_data(record):
    subset = {
        "level": record["level"].name,
        "time": record["time"].isoformat(timespec="seconds"),
    }
    subset["loc"] = extract_location(record)

    # This is where logger.contextualize() parameters can be added to the output
    for extra_key in ["trace", "url", "worksheet", "row"]:
        if extra_val := record.get("extra", {}).get(extra_key):
            subset[extra_key] = extra_val

    subset["message"] = record["message"]
    if exception := record.get("exception"):
        subset["exception"] = exception
    return subset


def serialize_for_console(record):
    subset = extract_log_data(record)
    subset.pop("message", None)
    subset.pop("level", None)
    subset.pop("loc", None)
    subset.pop("time", None)
    if not subset:
        return ""
    return json.dumps(subset, ensure_ascii=False)


def serialize(record):
    return json.dumps(extract_log_data(record), ensure_ascii=False)


def patching(record):
    record["extra"]["serialized"] = serialize(record)
    record["extra"]["serialize_for_console"] = serialize_for_console(record)


def format_for_human_readable_console():
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{file}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "{extra[serialize_for_console]} <level>{message}</level>"
    )


logger = logger.patch(patching)
