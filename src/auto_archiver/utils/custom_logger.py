from loguru import logger
import json


def extract_log_data(record):
    subset = {
        "level": record["level"].name,
        "time": record["time"].isoformat(timespec="seconds"),
    }
    subset["loc"] = f"{record['file'].name}:{record['function']}:{record['line']}"

    for extra_key in ["trace", "url", "worksheet", "row"]:
        if extra_val := record.get("extra", {}).get(extra_key):
            subset[extra_key] = extra_val

    subset["message"] = record["message"]
    if exception := record.get("exception"):
        subset["exception"] = exception
    return subset


def serialize_no_message(record):
    subset = extract_log_data(record)
    subset.pop("message", None)
    return json.dumps(subset, ensure_ascii=False)


def serialize(record):
    return json.dumps(extract_log_data(record), ensure_ascii=False)


def patching(record):
    record["extra"]["serialized"] = serialize(record)
    record["extra"]["serialize_no_message"] = serialize_no_message(record)


logger = logger.patch(patching)
