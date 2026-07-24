from __future__ import annotations

import argparse
from datetime import datetime, timezone

from auto_archiver.utils.custom_logger import logger

from .status_runner import run_status_checks, write_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--status-check",
        action="store_true",
        help="run platform status checks instead of a normal archiving run",
    )
    parser.add_argument(
        "--status-check-urls",
        dest="urls_path",
        default=None,
        help="path to a status_urls.yaml-style fixture (defaults to the bundled one)",
    )
    parser.add_argument(
        "--status-check-output",
        dest="output_path",
        default=None,
        help="path to write the JSON report to (defaults to ./status_report_<timestamp>.json)",
    )
    parser.add_argument(
        "--status-check-platforms",
        dest="platforms",
        nargs="+",
        default=None,
        help="limit the run to these platforms (defaults to all platforms in the fixture)",
    )
    return parser


def run_status_check_cli(args: list[str]) -> int:
    parsed = _build_parser().parse_args(args)

    results = run_status_checks(urls_path=parsed.urls_path, platforms=parsed.platforms)

    output_path = parsed.output_path or f"status_report_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    write_report(results, output_path)

    passed = sum(1 for r in results if r.is_content_accessible and r.is_content_archived)
    logger.info(f"Platform status check: {passed}/{len(results)} passed. Report written to {output_path}")
    for r in results:
        ok = r.is_content_accessible and r.is_content_archived
        logger.info(f"  [{'OK' if ok else 'FAIL'}] {r.platform_name}/{r.content_type}: {r.archive_url}")

    return 0 if passed == len(results) else 1
