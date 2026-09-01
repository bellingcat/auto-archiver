# Platform Status Checks

Auto Archiver includes a built-in status checker that tests whether each supported platform can currently be archived. It runs curated URLs through the real archiving pipeline and produces a structured JSON report.

This is useful for:
- Monitoring which platforms are currently working
- Comparing barebones vs. custom (proxy/auth) configurations
- Feeding results into a dashboard or CI pipeline

## Quick Start

```{code-block} console
auto-archiver-status
```

This runs all bundled test URLs through the pipeline with a minimal ("barebones") configuration and writes a timestamped JSON report to the current directory.

## CLI Options

| Flag | Description |
|------|-------------|
| `--platforms <name ...>` | Limit the run to specific platforms (e.g. `youtube bluesky`). |
| `--config <path>` | Path to an `orchestration.yaml` whose module settings (proxy, cookies, auth) are used for a second "custom" run alongside the barebones run. |
| `--urls <path>` | Path to a custom `status_urls.yaml` fixture. Defaults to the bundled one. |
| `--output`, `-o` | Path for the JSON report. Defaults to `./status_report_<timestamp>.json`. |

## Examples

**Check only YouTube and Bluesky:**

```{code-block} console
auto-archiver-status --platforms youtube bluesky
```

**Compare barebones vs. custom config (with proxy/auth):**

```{code-block} console
auto-archiver-status --config orchestration.yaml
```

This produces a side-by-side summary:

```text
platform/content_type               barebones    custom
-----------------------------------------------------------
bluesky/multi_image                 OK           OK
bluesky/single_image                OK           OK
bluesky/text_only                   OK           OK
bluesky/video                       OK           OK
youtube/video                       FAIL         OK
```

## JSON Report Format

The report is a JSON array of status records:

```json
[
  {
    "id": "2026-08-18T08:13:23+00:00_youtube_video_barebones",
    "run_datetime": "2026-08-18T08:13:23+00:00",
    "aa_version": "1.2.3",
    "platform_name": "youtube",
    "archive_url": "https://www.youtube.com/watch?v=...",
    "content_type": "video",
    "config_label": "barebones",
    "is_content_accessible": false,
    "is_content_archived": false,
    "current_metadata": { ... }
  }
]
```

| Field | Description |
|-------|-------------|
| `config_label` | `"barebones"` (no proxy/auth) or `"custom"` (with your orchestration config). |
| `is_content_accessible` | Whether the pipeline returned a successful, non-empty result. |
| `is_content_archived` | Whether expected media was downloaded and a title was extracted. |
| `current_metadata` | Raw metadata dict from the archiving run. |

## Custom Test URLs

You can provide your own test fixture via `--status-check-urls`. The YAML format:

```yaml
platform_name:
  - content_type: video
    url: https://example.com/some-video
    expect_media: true
  - content_type: text_only
    url: https://example.com/text-post
    expect_media: false
```

## Programmatic Usage

```python
from auto_archiver.modules.platform_status.status_runner import run_status_checks

results = run_status_checks(platforms=["bluesky"])
for r in results:
    print(f"{r.platform_name}/{r.content_type}: accessible={r.is_content_accessible}, archived={r.is_content_archived}")
```
