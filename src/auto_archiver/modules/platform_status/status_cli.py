from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone

from auto_archiver.utils.custom_logger import logger

from .status_runner import run_all_status_checks, write_report


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
    parser.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="path to an orchestration.yaml whose module settings (proxy, auth) are used for a second 'custom' run",
    )
    return parser


def _log_summary(results: list) -> None:
    """Log a per-platform/content_type summary grouped by config_label."""
    table: dict[tuple[str, str], dict[str, bool]] = defaultdict(dict)
    labels: set[str] = set()
    for r in results:
        ok = r.is_content_accessible and r.is_content_archived
        table[(r.platform_name, r.content_type)][r.config_label] = ok
        labels.add(r.config_label)

    sorted_labels = sorted(labels)
    header = f"  {'platform/content_type':<35s}" + "".join(f" {lbl:<12s}" for lbl in sorted_labels)
    logger.info(header)
    logger.info("  " + "-" * (35 + 12 * len(sorted_labels)))
    for (platform, ctype), by_label in sorted(table.items()):
        cells = ""
        for lbl in sorted_labels:
            if lbl in by_label:
                cells += f" {'OK':<12s}" if by_label[lbl] else f" {'FAIL':<12s}"
            else:
                cells += f" {'-':<12s}"
        logger.info(f"  {platform + '/' + ctype:<35s}{cells}")


def main(args: list[str] | None = None) -> None:
    parsed = _build_parser().parse_args(args)

    results = run_all_status_checks(
        urls_path=parsed.urls_path,
        platforms=parsed.platforms,
        config_path=parsed.config_path,
    )

    output_path = parsed.output_path or f"status_report_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    write_report(results, output_path)

    passed = sum(1 for r in results if r.is_content_accessible and r.is_content_archived)
    logger.info(f"Platform status check: {passed}/{len(results)} passed. Report written to {output_path}")
    _log_summary(results)

    sys.exit(0 if passed == len(results) else 1)
