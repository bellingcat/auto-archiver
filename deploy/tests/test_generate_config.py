"""Tests for deploy/generate_config.py – config generation from env vars."""

import json
import os
from unittest.mock import patch

import yaml

from deploy.generate_config import build_config, main


# ── Helpers ───────────────────────────────────────────────────────────


def _env(**overrides):
    """Return a clean env dict with only the given overrides (no leak from host)."""
    # Clear all deploy-relevant env vars, then apply overrides
    deploy_vars = [
        "LOG_LEVEL",
        "SUBTITLES",
        "GSHEET_URL",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "S3_BUCKET",
        "S3_KEY",
        "S3_SECRET",
        "S3_REGION",
        "S3_ENDPOINT",
        "S3_CDN_URL",
        "S3_PRIVATE",
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_BOT_TOKEN",
        "ENABLE_SCREENSHOTS",
        "ENABLE_THUMBNAILS",
        "ENABLE_CSV_DB",
    ]
    clean = {k: v for k, v in os.environ.items() if k not in deploy_vars}
    clean.update(overrides)
    return clean


# ── Base config (no optional env vars) ────────────────────────────────


class TestBaseConfig:
    """When no optional env vars are set, build_config returns a minimal working config."""

    def test_base_steps(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = build_config()
        steps = cfg["steps"]
        assert steps["feeders"] == ["cli_feeder"]
        assert steps["extractors"] == ["generic_extractor"]
        assert steps["enrichers"] == ["hash_enricher"]
        assert steps["databases"] == ["console_db"]
        assert steps["storages"] == ["local_storage"]
        assert steps["formatters"] == ["html_formatter"]

    def test_base_has_required_module_configs(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = build_config()
        assert "local_storage" in cfg
        assert "generic_extractor" in cfg
        assert "hash_enricher" in cfg
        assert "html_formatter" in cfg

    def test_default_log_level_is_info(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = build_config()
        assert cfg["logging"]["level"] == "INFO"

    def test_custom_log_level(self):
        with patch.dict(os.environ, _env(LOG_LEVEL="DEBUG"), clear=True):
            cfg = build_config()
        assert cfg["logging"]["level"] == "DEBUG"

    def test_authentication_present_and_empty(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = build_config()
        assert cfg["authentication"] == {}

    def test_local_storage_defaults(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = build_config()
        ls = cfg["local_storage"]
        assert ls["save_to"] == "/app/local_archive"
        assert ls["path_generator"] == "flat"
        assert ls["filename_generator"] == "static"

    def test_subtitles_default_false(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = build_config()
        assert cfg["generic_extractor"]["subtitles"] is False

    def test_subtitles_enabled(self):
        with patch.dict(os.environ, _env(SUBTITLES="true"), clear=True):
            cfg = build_config()
        assert cfg["generic_extractor"]["subtitles"] is True

    def test_subtitles_case_insensitive(self):
        with patch.dict(os.environ, _env(SUBTITLES="True"), clear=True):
            cfg = build_config()
        assert cfg["generic_extractor"]["subtitles"] is True

    def test_no_optional_modules_present(self):
        """Ensure optional modules don't appear when their env vars are absent."""
        with patch.dict(os.environ, _env(), clear=True):
            cfg = build_config()
        assert "gsheet_feeder" not in cfg
        assert "s3_storage" not in cfg
        assert "telegram_extractor" not in cfg
        assert "screenshot_enricher" not in cfg
        assert "thumbnail_enricher" not in cfg
        assert "csv_db" not in cfg

    def test_config_is_valid_yaml(self):
        """The output dict should round-trip through YAML cleanly."""
        with patch.dict(os.environ, _env(), clear=True):
            cfg = build_config()
        dumped = yaml.dump(cfg)
        reloaded = yaml.safe_load(dumped)
        assert reloaded == cfg


# ── Google Sheets ─────────────────────────────────────────────────────


class TestGSheetConfig:
    def test_gsheet_adds_feeder_and_db(self):
        with patch.dict(os.environ, _env(GSHEET_URL="https://docs.google.com/spreadsheets/d/abc"), clear=True):
            cfg = build_config()
        assert "gsheet_feeder" in cfg["steps"]["feeders"]
        assert "gsheet_db" in cfg["steps"]["databases"]

    def test_gsheet_feeder_config(self):
        url = "https://docs.google.com/spreadsheets/d/abc123"
        with patch.dict(os.environ, _env(GSHEET_URL=url), clear=True):
            cfg = build_config()
        gf = cfg["gsheet_feeder"]
        assert gf["sheet"] == url
        assert gf["header"] == 1
        assert "service_account" in gf
        assert gf["columns"]["url"] == "link"
        assert gf["columns"]["status"] == "archive status"

    def test_gsheet_preserves_cli_feeder(self):
        """cli_feeder should still be present even when gsheet is added."""
        with patch.dict(os.environ, _env(GSHEET_URL="https://example.com/sheet"), clear=True):
            cfg = build_config()
        assert "cli_feeder" in cfg["steps"]["feeders"]

    def test_service_account_json_written(self, tmp_path):
        """When GOOGLE_SERVICE_ACCOUNT_JSON is set, it writes the file."""
        sa_data = json.dumps({"type": "service_account", "project_id": "test"})
        secrets_dir = tmp_path / "secrets"
        with (
            patch.dict(os.environ, _env(GOOGLE_SERVICE_ACCOUNT_JSON=sa_data), clear=True),
            patch("deploy.generate_config.SECRETS_DIR", secrets_dir),
        ):
            build_config()
        sa_path = secrets_dir / "service_account.json"
        assert sa_path.exists()
        assert json.loads(sa_path.read_text())["project_id"] == "test"


# ── S3 storage ────────────────────────────────────────────────────────


class TestS3Config:
    def test_s3_adds_storage(self):
        with patch.dict(os.environ, _env(S3_BUCKET="my-bucket"), clear=True):
            cfg = build_config()
        assert "s3_storage" in cfg["steps"]["storages"]
        assert "local_storage" in cfg["steps"]["storages"]  # local still there

    def test_s3_config_values(self):
        env = _env(
            S3_BUCKET="my-bucket",
            S3_KEY="AKID",
            S3_SECRET="shhh",
            S3_REGION="eu-west-1",
        )
        with patch.dict(os.environ, env, clear=True):
            cfg = build_config()
        s3 = cfg["s3_storage"]
        assert s3["bucket"] == "my-bucket"
        assert s3["key"] == "AKID"
        assert s3["secret"] == "shhh"
        assert s3["region"] == "eu-west-1"
        assert s3["private"] is False
        assert s3["random_no_duplicate"] is True

    def test_s3_defaults(self):
        with patch.dict(os.environ, _env(S3_BUCKET="b"), clear=True):
            cfg = build_config()
        s3 = cfg["s3_storage"]
        assert s3["region"] == "us-east-1"
        assert "{region}" in s3["endpoint_url"]

    def test_s3_private_flag(self):
        with patch.dict(os.environ, _env(S3_BUCKET="b", S3_PRIVATE="true"), clear=True):
            cfg = build_config()
        assert cfg["s3_storage"]["private"] is True

    def test_s3_custom_endpoint(self):
        endpoint = "https://nyc3.digitaloceanspaces.com"
        with patch.dict(os.environ, _env(S3_BUCKET="b", S3_ENDPOINT=endpoint), clear=True):
            cfg = build_config()
        assert cfg["s3_storage"]["endpoint_url"] == endpoint


# ── Telegram ──────────────────────────────────────────────────────────


class TestTelegramConfig:
    def test_telegram_added_when_both_set(self):
        env = _env(TELEGRAM_API_ID="12345", TELEGRAM_API_HASH="abc")
        with patch.dict(os.environ, env, clear=True):
            cfg = build_config()
        assert "telegram_extractor" in cfg["steps"]["extractors"]
        assert cfg["telegram_extractor"]["api_id"] == "12345"
        assert cfg["telegram_extractor"]["api_hash"] == "abc"

    def test_telegram_not_added_if_only_id(self):
        with patch.dict(os.environ, _env(TELEGRAM_API_ID="12345"), clear=True):
            cfg = build_config()
        assert "telegram_extractor" not in cfg["steps"]["extractors"]

    def test_telegram_not_added_if_only_hash(self):
        with patch.dict(os.environ, _env(TELEGRAM_API_HASH="abc"), clear=True):
            cfg = build_config()
        assert "telegram_extractor" not in cfg["steps"]["extractors"]

    def test_telegram_bot_token_optional(self):
        env = _env(TELEGRAM_API_ID="12345", TELEGRAM_API_HASH="abc", TELEGRAM_BOT_TOKEN="bot:tok")
        with patch.dict(os.environ, env, clear=True):
            cfg = build_config()
        assert cfg["telegram_extractor"]["bot_token"] == "bot:tok"

    def test_telegram_no_bot_token(self):
        env = _env(TELEGRAM_API_ID="12345", TELEGRAM_API_HASH="abc")
        with patch.dict(os.environ, env, clear=True):
            cfg = build_config()
        assert "bot_token" not in cfg["telegram_extractor"]


# ── Optional enrichers / databases ────────────────────────────────────


class TestOptionalModules:
    def test_screenshots_disabled_by_default(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = build_config()
        assert "screenshot_enricher" not in cfg["steps"]["enrichers"]

    def test_screenshots_enabled(self):
        with patch.dict(os.environ, _env(ENABLE_SCREENSHOTS="true"), clear=True):
            cfg = build_config()
        assert "screenshot_enricher" in cfg["steps"]["enrichers"]
        assert cfg["screenshot_enricher"]["width"] == 1280

    def test_thumbnails_enabled(self):
        with patch.dict(os.environ, _env(ENABLE_THUMBNAILS="true"), clear=True):
            cfg = build_config()
        assert "thumbnail_enricher" in cfg["steps"]["enrichers"]
        assert cfg["thumbnail_enricher"]["max_thumbnails"] == 16

    def test_csv_db_enabled(self):
        with patch.dict(os.environ, _env(ENABLE_CSV_DB="true"), clear=True):
            cfg = build_config()
        assert "csv_db" in cfg["steps"]["databases"]
        assert cfg["csv_db"]["csv_file"] == "/app/local_archive/db.csv"

    def test_case_insensitive_boolean(self):
        with patch.dict(os.environ, _env(ENABLE_SCREENSHOTS="TRUE"), clear=True):
            cfg = build_config()
        assert "screenshot_enricher" in cfg["steps"]["enrichers"]


# ── Combined / full config ────────────────────────────────────────────


class TestCombinedConfig:
    def test_all_optional_modules_together(self):
        """Enable everything at once and verify no conflicts."""
        env = _env(
            GSHEET_URL="https://example.com/sheet",
            S3_BUCKET="bucket",
            S3_KEY="key",
            S3_SECRET="secret",
            TELEGRAM_API_ID="123",
            TELEGRAM_API_HASH="abc",
            TELEGRAM_BOT_TOKEN="tok",
            ENABLE_SCREENSHOTS="true",
            ENABLE_THUMBNAILS="true",
            ENABLE_CSV_DB="true",
        )
        with patch.dict(os.environ, env, clear=True):
            cfg = build_config()

        steps = cfg["steps"]
        assert "gsheet_feeder" in steps["feeders"]
        assert "telegram_extractor" in steps["extractors"]
        assert "screenshot_enricher" in steps["enrichers"]
        assert "thumbnail_enricher" in steps["enrichers"]
        assert "csv_db" in steps["databases"]
        assert "gsheet_db" in steps["databases"]
        assert "s3_storage" in steps["storages"]
        assert "local_storage" in steps["storages"]

        # All module configs present
        for key in [
            "gsheet_feeder",
            "s3_storage",
            "telegram_extractor",
            "screenshot_enricher",
            "thumbnail_enricher",
            "csv_db",
        ]:
            assert key in cfg, f"{key} config missing"

    def test_full_config_valid_yaml(self):
        env = _env(
            GSHEET_URL="https://example.com/sheet",
            S3_BUCKET="bucket",
            TELEGRAM_API_ID="123",
            TELEGRAM_API_HASH="abc",
            ENABLE_SCREENSHOTS="true",
            ENABLE_CSV_DB="true",
        )
        with patch.dict(os.environ, env, clear=True):
            cfg = build_config()
        dumped = yaml.dump(cfg)
        reloaded = yaml.safe_load(dumped)
        assert reloaded == cfg


# ── main() writes file ───────────────────────────────────────────────


class TestMainFunction:
    def test_main_writes_config_file(self, tmp_path):
        config_path = tmp_path / "orchestration.yaml"
        with patch.dict(os.environ, _env(), clear=True), patch("deploy.generate_config.CONFIG_PATH", config_path):
            main()
        assert config_path.exists()
        cfg = yaml.safe_load(config_path.read_text())
        assert cfg["steps"]["feeders"] == ["cli_feeder"]

    def test_main_creates_parent_dirs(self, tmp_path):
        config_path = tmp_path / "nested" / "dir" / "orchestration.yaml"
        with patch.dict(os.environ, _env(), clear=True), patch("deploy.generate_config.CONFIG_PATH", config_path):
            main()
        assert config_path.exists()
