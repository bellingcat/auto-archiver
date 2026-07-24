import json

import pytest

from auto_archiver.core.media import Media
from auto_archiver.core.metadata import Metadata
from auto_archiver.modules.platform_status.status_runner import (
    evaluate_result,
    iter_cases,
    load_status_urls,
    run_status_checks,
    write_report,
)


def make_metadata(url: str, title: str = "", media: list[Media] = None, success: bool = True) -> Metadata:
    m = Metadata().set_url(url)
    if title:
        m.set_title(title)
    if success:
        m.success("test")
    for media_item in media or []:
        m.add_media(media_item)
    return m


def make_media(tmp_path, filename: str = "file.mp4", size: int = 100) -> Media:
    path = tmp_path / filename
    path.write_bytes(b"x" * size)
    media = Media(filename=str(path))
    media.add_url(str(path))
    return media


class TestLoadStatusUrls:
    def test_loads_bundled_fixture(self):
        urls_by_platform = load_status_urls()

        assert len(urls_by_platform) > 0
        for cases in urls_by_platform.values():
            assert len(cases) > 0
            for case in cases:
                assert case.keys() >= {"content_type", "url", "expect_media"}


class TestIterCases:
    def test_iterates_all_cases_by_default(self):
        urls_by_platform = load_status_urls()
        cases = list(iter_cases(urls_by_platform))
        total_cases = sum(len(v) for v in urls_by_platform.values())

        assert len(cases) == total_cases

    def test_filters_by_platform(self):
        urls_by_platform = load_status_urls()
        first_platform = next(iter(urls_by_platform))

        cases = list(iter_cases(urls_by_platform, platforms=[first_platform]))

        assert len(cases) == len(urls_by_platform[first_platform])
        assert all(platform_name == first_platform for platform_name, _ in cases)


class TestEvaluateResult:
    def test_media_and_title_present_passes(self, tmp_path):
        media = make_media(tmp_path)
        metadata = make_metadata("https://example.com/video-post", title="A real title", media=[media])
        case = {"url": "https://example.com/video-post", "content_type": "video", "expect_media": True}

        status = evaluate_result(metadata, case, "exampleplatform")

        assert status.is_content_accessible
        assert status.is_content_archived
        assert status.platform_name == "exampleplatform"
        assert status.content_type == "video"

    def test_missing_media_when_expected_fails(self):
        metadata = make_metadata("https://example.com/video-post", title="A real title", media=[])
        case = {"url": "https://example.com/video-post", "content_type": "video", "expect_media": True}

        status = evaluate_result(metadata, case, "exampleplatform")

        assert not status.is_content_archived

    def test_empty_title_fails(self, tmp_path):
        media = make_media(tmp_path)
        metadata = make_metadata("https://example.com/video-post", title="", media=[media])
        case = {"url": "https://example.com/video-post", "content_type": "video", "expect_media": True}

        status = evaluate_result(metadata, case, "exampleplatform")

        assert not status.is_content_archived

    def test_zero_byte_media_fails(self, tmp_path):
        media = make_media(tmp_path, size=0)
        metadata = make_metadata("https://example.com/video-post", title="A real title", media=[media])
        case = {"url": "https://example.com/video-post", "content_type": "video", "expect_media": True}

        status = evaluate_result(metadata, case, "exampleplatform")

        assert not status.is_content_archived

    def test_expect_media_false_passes_without_media(self):
        metadata = make_metadata("https://example.com/text-post", title="A real title", media=[])
        case = {"url": "https://example.com/text-post", "content_type": "text_only", "expect_media": False}

        status = evaluate_result(metadata, case, "exampleplatform")

        assert status.is_content_archived

    def test_failed_metadata_is_not_accessible(self):
        metadata = Metadata().set_url("https://example.com/video-post")
        case = {"url": "https://example.com/video-post", "content_type": "video", "expect_media": True}

        status = evaluate_result(metadata, case, "exampleplatform")

        assert not status.is_content_accessible
        assert not status.is_content_archived


class TestWriteReport:
    def test_writes_valid_json_matching_schema(self, tmp_path):
        metadata = make_metadata("https://example.com/text-post", title="A real title")
        case = {"url": "https://example.com/text-post", "content_type": "text_only", "expect_media": False}
        status = evaluate_result(metadata, case, "exampleplatform")

        out_path = str(tmp_path / "report.json")
        write_report([status], out_path)

        with open(out_path) as f:
            records = json.load(f)

        assert len(records) == 1
        record = records[0]
        for key in [
            "id",
            "run_datetime",
            "aa_version",
            "platform_name",
            "archive_url",
            "content_type",
            "is_content_accessible",
            "is_content_archived",
            "current_metadata",
        ]:
            assert key in record

    def test_serializes_datetime_metadata_without_error(self, tmp_path):
        # Metadata.metadata commonly contains real datetime objects (e.g. _processed_at,
        # timestamp) copied verbatim into current_metadata - this must not crash json.dump
        metadata = make_metadata("https://example.com/text-post", title="A real title")
        case = {"url": "https://example.com/text-post", "content_type": "text_only", "expect_media": False}
        status = evaluate_result(metadata, case, "exampleplatform")

        out_path = str(tmp_path / "report.json")
        write_report([status], out_path)  # should not raise

        with open(out_path) as f:
            json.load(f)  # should still be valid JSON


@pytest.mark.download
class TestRunStatusChecksLive:
    """Live integration test - runs a small real subset through the actual pipeline."""

    def test_run_status_checks_tiktok(self):
        results = run_status_checks(platforms=["tiktok"])

        assert len(results) == 1
        assert results[0].is_content_accessible
        assert results[0].is_content_archived
