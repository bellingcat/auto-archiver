from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from auto_archiver.utils.custom_logger import logger

from .status_runner import run_status_checks, write_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auto-archiver-status",
        description="Run platform status checks and produce a JSON report.",
    )
    parser.add_argument(
        "--urls",
        dest="urls_path",
        default=None,
        help="path to a status_urls.yaml fixture (defaults to the bundled one)",
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output_path",
        default=None,
        help="path to write the JSON report (defaults to ./status_report_<timestamp>.json)",
    )
    parser.add_argument(
        "--platforms",
        nargs="+",
        default=None,
        help="limit the run to specific platforms (e.g. youtube bluesky)",
    )
    return parser


def main(args: list[str] | None = None) -> None:
    parsed = _build_parser().parse_args(args)

    results = run_status_checks(urls_path=parsed.urls_path, platforms=parsed.platforms)

    output_path = parsed.output_path or f"status_report_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    write_report(results, output_path)

    passed = sum(1 for r in results if r.is_content_accessible and r.is_content_archived)
    logger.info(f"Platform status check: {passed}/{len(results)} passed. Report written to {output_path}")
    for r in results:
        ok = r.is_content_accessible and r.is_content_archived
        logger.info(f"  [{'OK' if ok else 'FAIL'}] {r.platform_name}/{r.content_type}: {r.archive_url}")

    sys.exit(0 if passed == len(results) else 1)
