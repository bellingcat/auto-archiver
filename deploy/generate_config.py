#!/usr/bin/env python3
"""
Generates orchestration.yaml from environment variables.

This script bridges Railway's env-var-based configuration with
auto-archiver's YAML-based configuration system. It runs at container
startup before the web UI server starts.
"""

import os
from pathlib import Path

import yaml


CONFIG_PATH = Path("/app/secrets/orchestration.yaml")
SECRETS_DIR = Path("/app/secrets")


def build_config() -> dict:
    """Build an orchestration config dict from environment variables."""

    # -- Base config: always present ------------------------------------
    config = {
        "steps": {
            "feeders": ["cli_feeder"],
            "extractors": ["generic_extractor"],
            "enrichers": ["hash_enricher"],
            "databases": ["console_db"],
            "storages": ["local_storage"],
            "formatters": ["html_formatter"],
        },
        "logging": {
            "level": os.environ.get("LOG_LEVEL", "INFO"),
        },
        "local_storage": {
            "save_to": "/app/local_archive",
            "path_generator": "flat",
            "filename_generator": "static",
        },
        "generic_extractor": {
            "subtitles": os.environ.get("SUBTITLES", "false").lower() == "true",
            "comments": False,
            "livestreams": False,
            "live_from_start": False,
            "end_means_success": True,
            "allow_playlist": False,
        },
        "hash_enricher": {
            "algorithm": "SHA-256",
        },
        "html_formatter": {
            "detect_thumbnails": True,
        },
        "authentication": {},
    }

    # -- Google Sheets feeder (optional) --------------------------------
    gsheet_url = os.environ.get("GSHEET_URL", "")
    if gsheet_url:
        config["steps"]["feeders"].append("gsheet_feeder")
        config["steps"]["databases"].append("gsheet_db")
        config["gsheet_feeder"] = {
            "sheet": gsheet_url,
            "header": 1,
            "service_account": str(SECRETS_DIR / "service_account.json"),
            "use_sheet_names_in_stored_paths": False,
            "columns": {
                "url": "link",
                "status": "archive status",
                "folder": "destination folder",
                "archive": "archive location",
                "date": "archive date",
                "thumbnail": "thumbnail",
                "timestamp": "upload timestamp",
                "title": "upload title",
                "text": "textual content",
                "screenshot": "screenshot",
                "hash": "hash",
                "pdq_hash": "perceptual hashes",
            },
        }

    # -- Google service account JSON (optional) -------------------------
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if sa_json:
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        sa_path = SECRETS_DIR / "service_account.json"
        sa_path.write_text(sa_json)
        print(f"[deploy] Wrote Google service account to {sa_path}")

    # -- S3 storage (optional) ------------------------------------------
    s3_bucket = os.environ.get("S3_BUCKET", "")
    if s3_bucket:
        config["steps"]["storages"].append("s3_storage")
        config["s3_storage"] = {
            "bucket": s3_bucket,
            "region": os.environ.get("S3_REGION", "us-east-1"),
            "key": os.environ.get("S3_KEY", ""),
            "secret": os.environ.get("S3_SECRET", ""),
            "endpoint_url": os.environ.get("S3_ENDPOINT", "https://s3.{region}.amazonaws.com"),
            "cdn_url": os.environ.get(
                "S3_CDN_URL",
                "https://{bucket}.s3.{region}.amazonaws.com/{key}",
            ),
            "private": os.environ.get("S3_PRIVATE", "false").lower() == "true",
            "random_no_duplicate": True,
            "key_path": "random",
        }

    # -- Telegram extractor (optional) ----------------------------------
    tg_api_id = os.environ.get("TELEGRAM_API_ID", "")
    tg_api_hash = os.environ.get("TELEGRAM_API_HASH", "")
    if tg_api_id and tg_api_hash:
        config["steps"]["extractors"].append("telegram_extractor")
        config["telegram_extractor"] = {
            "api_id": tg_api_id,
            "api_hash": tg_api_hash,
        }
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if bot_token:
            config["telegram_extractor"]["bot_token"] = bot_token

    # -- Screenshot enricher (optional) ---------------------------------
    if os.environ.get("ENABLE_SCREENSHOTS", "").lower() == "true":
        config["steps"]["enrichers"].append("screenshot_enricher")
        config["screenshot_enricher"] = {
            "width": 1280,
            "height": 7200,
            "save_to_pdf": True,
        }

    # -- Thumbnail enricher (optional) ----------------------------------
    if os.environ.get("ENABLE_THUMBNAILS", "").lower() == "true":
        config["steps"]["enrichers"].append("thumbnail_enricher")
        config["thumbnail_enricher"] = {
            "thumbnails_per_minute": 60,
            "max_thumbnails": 16,
        }

    # -- CSV database (optional) ----------------------------------------
    if os.environ.get("ENABLE_CSV_DB", "").lower() == "true":
        config["steps"]["databases"].append("csv_db")
        config["csv_db"] = {
            "csv_file": "/app/local_archive/db.csv",
        }

    return config


def main():
    config = build_config()

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"[deploy] Generated config at {CONFIG_PATH}")
    print(f"[deploy] Active steps: {config['steps']}")


if __name__ == "__main__":
    main()
