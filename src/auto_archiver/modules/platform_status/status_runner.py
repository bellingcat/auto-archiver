from __future__ import annotations

import json
import os
from tempfile import TemporaryDirectory
from typing import Any

import yaml

from auto_archiver.core import Metadata
from auto_archiver.core.orchestrator import ArchivingOrchestrator
from auto_archiver.utils.custom_logger import logger

from .platform_status import PlatformStatus

DEFAULT_URLS_PATH = os.path.join(os.path.dirname(__file__), "status_urls.yaml")

MIN_TITLE_LENGTH = 3


def load_status_urls(path: str | None = None) -> dict[str, list[dict[str, Any]]]:
    """Loads the platform -> [case, ...] mapping used to drive status checks."""
    with open(path or DEFAULT_URLS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def iter_cases(urls_by_platform: dict[str, list[dict[str, Any]]], platforms: list[str] | None = None):
    for platform_name, cases in urls_by_platform.items():
        if platforms and platform_name not in platforms:
            continue
        for case in cases:
            yield platform_name, case


def _build_cli_args(urls: list[str], config_path: str, save_to: str) -> list[str]:
    """Builds a minimal CLI-style args list that runs the given URLs through the real
    pipeline: cli_feeder -> generic_extractor -> console_db (log-only) -> local_storage.
    """
    return [
        "--config",
        config_path,
        "--feeders",
        "cli_feeder",
        "--extractors",
        "generic_extractor",
        "--generic_extractor.ytdlp_update_interval",
        "-1",
        "--generic_extractor.end_means_success",
        "true",
        "--enrichers",
        "meta_enricher",
        "--databases",
        "console_db",
        "--storages",
        "local_storage",
        "--local_storage.save_to",
        save_to,
        "--formatters",
        "html_formatter",
        "--",
        *urls,
    ]


def _media_is_sane(media) -> bool:
    if not media.urls:
        return False
    return all(os.path.exists(u) and os.path.getsize(u) > 0 for u in media.urls)


def evaluate_result(metadata: Metadata, case: dict[str, Any], platform_name: str) -> PlatformStatus:
    """Applies coarse pass/sanity checks to a pipeline result: media presence (when
    expected) and a non-trivial title/description.
    """
    status = PlatformStatus.from_metadata(
        metadata,
        platform_name=platform_name,
        archive_url=case["url"],
        content_type=case["content_type"],
    )

    status.content_accessible(metadata.is_success() and not metadata.is_empty())

    expect_media = case.get("expect_media", True)
    if expect_media:
        media_ok = len(metadata.media) > 0 and all(_media_is_sane(m) for m in metadata.media)
    else:
        media_ok = True

    title = metadata.get_title() or ""
    title_ok = len(title.strip()) >= MIN_TITLE_LENGTH

    status.content_archived(media_ok and title_ok)

    return status


def _resolve_url(metadata: Metadata) -> str:
    """Return the original input URL for a metadata result, falling back to the
    (possibly sanitized) current URL.
    """
    return metadata.metadata.get("original_url", metadata.get_url())


def run_status_checks(
    urls_path: str | None = None,
    platforms: list[str] | None = None,
) -> list[PlatformStatus]:
    """Runs every configured status-check URL through the real archiving pipeline and
    returns one PlatformStatus per URL.
    """
    urls_by_platform = load_status_urls(urls_path)
    cases = list(iter_cases(urls_by_platform, platforms))
    if not cases:
        return []

    cases_by_url = {case["url"]: (platform_name, case) for platform_name, case in cases}

    with TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "orchestration.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("steps: {}\n")
        save_to = os.path.join(tmpdir, "archived")

        args = _build_cli_args(list(cases_by_url.keys()), config_path, save_to)
        orchestrator = ArchivingOrchestrator()
        orchestrator.setup(args)

        results = []
        for metadata in orchestrator.feed():
            if metadata is None:
                continue
            url = _resolve_url(metadata)
            if url not in cases_by_url:
                logger.warning(f"Status check: URL '{url}' not found in cases (possibly rewritten by extractor)")
                continue
            platform_name, case = cases_by_url[url]
            results.append(evaluate_result(metadata, case, platform_name))

    return results


def write_report(results: list[PlatformStatus], out_path: str) -> None:
    records = [r.to_record() for r in results]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, default=str)
