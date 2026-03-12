#!/usr/bin/env python3
"""
Startup entrypoint for cloud deployments.

1. Generates orchestration.yaml from environment variables
2. Starts the Google Sheets poller (if GSHEET_URL is set)
3. Starts the FastAPI web UI
"""

import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

# Generate config from env vars
from deploy.generate_config import main as generate_config  # noqa: E402

generate_config()

# Start gsheet poller (no-op if GSHEET_URL not set)
from deploy.gsheet_poller import start_poller  # noqa: E402

start_poller()

# Start web server
import uvicorn  # noqa: E402

port = int(os.environ.get("PORT", "8080"))
uvicorn.run(
    "deploy.web_ui:app",
    host="0.0.0.0",
    port=port,
    log_level="info",
)
