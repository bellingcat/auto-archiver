#!/usr/bin/env python3
"""
Background Google Sheets poller for auto-archiver cloud deployments.

When GSHEET_URL is set, periodically runs auto-archiver with gsheet_feeder
to check for new URLs in the configured spreadsheet. Runs as a daemon thread
alongside the web UI.
"""

import logging
import os
import subprocess
import threading
import time

logger = logging.getLogger("gsheet_poller")

CONFIG_PATH = "/app/secrets/orchestration.yaml"


def _poll_once():
    """Run auto-archiver once to process any new rows in the Google Sheet."""
    logger.info("Polling Google Sheet for new URLs...")
    try:
        result = subprocess.run(
            ["python3", "-m", "auto_archiver", "--config", CONFIG_PATH],
            capture_output=True,
            text=True,
            cwd="/app",
            timeout=600,  # 10 minute timeout per poll
        )
        if result.returncode == 0:
            logger.info("Sheet poll completed successfully.")
        else:
            logger.warning("Sheet poll exited with code %d: %s", result.returncode, result.stderr[-500:])
    except subprocess.TimeoutExpired:
        logger.error("Sheet poll timed out after 600s")
    except Exception:
        logger.exception("Sheet poll failed")


def _poll_loop(interval: int):
    """Run the poll loop at the given interval (seconds)."""
    logger.info("Google Sheets poller started (interval=%ds)", interval)
    while True:
        _poll_once()
        time.sleep(interval)


def start_poller():
    """
    Start the Google Sheets poller as a daemon thread if GSHEET_URL is set.
    Call this once at application startup.
    """
    gsheet_url = os.environ.get("GSHEET_URL", "")
    if not gsheet_url:
        logger.info("GSHEET_URL not set – Sheet poller disabled.")
        return

    interval = int(os.environ.get("POLL_INTERVAL", "300"))
    if interval < 60:
        interval = 60  # minimum 1 minute

    thread = threading.Thread(
        target=_poll_loop,
        args=(interval,),
        daemon=True,
        name="gsheet-poller",
    )
    thread.start()
    logger.info("Google Sheets poller thread started.")
