import pytest
import requests
import os
from unittest.mock import MagicMock

from auto_archiver.modules.ghostarchive_enricher.ghostarchive_enricher import GhostarchiveEnricher

CI = os.getenv("GITHUB_ACTIONS", "") == "true"

# sample HTML responses for mocking
SEARCH_HTML_FOUND = """
<html><body>
<h1>Archives for https://example.com</h1>
<table>
<tr><td><a href="http://ghostarchive.org/archive/Abc12">https://example.com</a></td></tr>
</table>
</body></html>
"""

SEARCH_HTML_NOT_FOUND = """
<html><body>
<h1>Archives for https://example.com</h1>
<p>Page 0 out of 0</p>
<p>No archives for that site.</p>
</body></html>
"""

SAVE_RESPONSE_HTML_WITH_LINK = """
<html><body>
<h1>Archive saved</h1>
<a href="/archive/Xyz99">View archive</a>
</body></html>
"""

ENRICHER_CONFIG = {
    "timeout": 120,
    "check_existing": True,
    "proxy_http": None,
    "proxy_https": None,
}


class TestGhostarchiveEnricher:
    """Tests for Ghost Archive Enricher"""

    @pytest.fixture(autouse=True)
    def setup_enricher(self, setup_module):
        self.enricher: GhostarchiveEnricher = setup_module("ghostarchive_enricher", ENRICHER_CONFIG)

    def test_search_existing_found(self, mocker):
        """When an existing archive is found, it should be returned."""
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.text = SEARCH_HTML_FOUND
        mocker.patch(
            "auto_archiver.modules.ghostarchive_enricher.ghostarchive_enricher.requests.get", return_value=mock_response
        )

        result = self.enricher._search_existing("https://example.com")
        assert result == "https://ghostarchive.org/archive/Abc12"

    def test_search_existing_not_found(self, mocker):
        """When no existing archive is found, None should be returned."""
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.text = SEARCH_HTML_NOT_FOUND
        mocker.patch(
            "auto_archiver.modules.ghostarchive_enricher.ghostarchive_enricher.requests.get", return_value=mock_response
        )

        result = self.enricher._search_existing("https://example.com")
        assert result is None

    def test_search_existing_request_error(self, mocker):
        """When search request fails, None should be returned."""
        mocker.patch(
            "auto_archiver.modules.ghostarchive_enricher.ghostarchive_enricher.requests.get",
            side_effect=requests.exceptions.ConnectionError("connection failed"),
        )

        result = self.enricher._search_existing("https://example.com")
        assert result is None

    def test_search_existing_non_200(self, mocker):
        """When search returns non-200, None should be returned."""
        mock_response = mocker.Mock()
        mock_response.status_code = 503
        mocker.patch(
            "auto_archiver.modules.ghostarchive_enricher.ghostarchive_enricher.requests.get", return_value=mock_response
        )

        result = self.enricher._search_existing("https://example.com")
        assert result is None

    def test_submit_url_success_redirect(self, mocker):
        """Successful submission via headless browser should return archive URL."""
        mock_sb = MagicMock()
        mock_sb.get_current_url.return_value = "https://ghostarchive.org/archive/NewId1"
        mock_sb.__enter__ = MagicMock(return_value=mock_sb)
        mock_sb.__exit__ = MagicMock(return_value=False)

        mocker.patch("auto_archiver.modules.ghostarchive_enricher.ghostarchive_enricher.SB", return_value=mock_sb)

        result = self.enricher._submit_url("https://example.com")
        assert result == "https://ghostarchive.org/archive/NewId1"
        mock_sb.type.assert_called_once()
        mock_sb.click.assert_called_once()

    def test_submit_url_success_redirect_strips_query(self, mocker):
        """Redirect URL query params should be stripped."""
        mock_sb = MagicMock()
        mock_sb.get_current_url.return_value = "https://ghostarchive.org/archive/NewId1?wr=false"
        mock_sb.__enter__ = MagicMock(return_value=mock_sb)
        mock_sb.__exit__ = MagicMock(return_value=False)

        mocker.patch("auto_archiver.modules.ghostarchive_enricher.ghostarchive_enricher.SB", return_value=mock_sb)

        result = self.enricher._submit_url("https://example.com")
        assert result == "https://ghostarchive.org/archive/NewId1"

    def test_submit_url_success_html_fallback(self, mocker):
        """When browser doesn't redirect, should parse page source for archive link."""
        mock_sb = MagicMock()
        mock_sb.get_current_url.return_value = "https://ghostarchive.org/archive2"
        mock_sb.get_page_source.return_value = SAVE_RESPONSE_HTML_WITH_LINK
        mock_sb.__enter__ = MagicMock(return_value=mock_sb)
        mock_sb.__exit__ = MagicMock(return_value=False)

        # make timeout=0 so the polling loop exits immediately and falls through to HTML parsing
        self.enricher.timeout = 0
        mocker.patch("auto_archiver.modules.ghostarchive_enricher.ghostarchive_enricher.SB", return_value=mock_sb)

        result = self.enricher._submit_url("https://example.com")
        assert result == "https://ghostarchive.org/archive/Xyz99"

    def test_submit_url_browser_error(self, mocker):
        """Browser error during submission should return None."""
        mocker.patch(
            "auto_archiver.modules.ghostarchive_enricher.ghostarchive_enricher.SB",
            side_effect=Exception("browser failed to start"),
        )

        result = self.enricher._submit_url("https://example.com")
        assert result is None

    def test_proxy_configuration(self, mocker):
        """Proxies should be passed to search requests when configured."""
        self.enricher.proxy_http = "http://proxy:8080"
        self.enricher.proxy_https = "https://proxy:8443"

        mock_get = mocker.patch(
            "auto_archiver.modules.ghostarchive_enricher.ghostarchive_enricher.requests.get",
        )
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.text = SEARCH_HTML_FOUND
        mock_get.return_value = mock_response

        result = self.enricher._search_existing("https://example.com")

        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs.get("proxies") == {"http": "http://proxy:8080", "https": "https://proxy:8443"}
        assert result is not None

    def test_parse_archive_url_with_replay_links(self):
        """Parser should ignore /replay/ links and only return /archive/ links."""
        html = """
        <html><body>
        <a href="/archive/replay/w/id-abc/mp_/https://example.com">replay</a>
        <a href="/archive/Valid1">valid</a>
        </body></html>
        """
        result = self.enricher._parse_archive_url(html)
        assert result == "https://ghostarchive.org/archive/Valid1"

    def test_parse_archive_url_no_links(self):
        """Parser should return None when no archive links found."""
        html = "<html><body><p>No archive here</p></body></html>"
        result = self.enricher._parse_archive_url(html)
        assert result is None

    def test_enrich_sets_ghostarchive_on_metadata(self, mocker, make_item):
        """enrich() should set 'ghostarchive' key on the metadata object."""
        mocker.patch.object(self.enricher, "_search_existing", return_value="https://ghostarchive.org/archive/Enr1")

        item = make_item("https://example.com")
        result = self.enricher.enrich(item)

        assert result is True
        assert item.get("ghostarchive") == "https://ghostarchive.org/archive/Enr1"

    def test_enrich_skips_if_already_enriched(self, mocker, make_item):
        """enrich() should skip if ghostarchive key is already set."""
        mock_search = mocker.patch.object(self.enricher, "_search_existing")

        item = make_item("https://example.com", ghostarchive="https://ghostarchive.org/archive/Old1")
        result = self.enricher.enrich(item)

        assert result is True
        mock_search.assert_not_called()

    def test_enrich_returns_false_on_failure(self, mocker, make_item):
        """enrich() should return False when both search and submit fail."""
        mocker.patch.object(self.enricher, "_search_existing", return_value=None)
        mocker.patch.object(self.enricher, "_submit_url", return_value=None)

        item = make_item("https://example.com")
        result = self.enricher.enrich(item)

        assert result is False

    def test_enrich_skips_auth_wall(self, mocker, make_item):
        """enrich() should skip URLs behind auth walls."""
        mocker.patch(
            "auto_archiver.modules.ghostarchive_enricher.ghostarchive_enricher.UrlUtil.is_auth_wall", return_value=True
        )

        item = make_item("https://example.com/login")
        result = self.enricher.enrich(item)
        assert result is False

    def test_enrich_with_existing_archive(self, mocker, make_item):
        """enrich() should use existing archive when check_existing is True."""
        mocker.patch.object(self.enricher, "_search_existing", return_value="https://ghostarchive.org/archive/Exist1")
        mock_submit = mocker.patch.object(self.enricher, "_submit_url")

        item = make_item("https://example.com")
        result = self.enricher.enrich(item)

        assert result is True
        assert item.get("ghostarchive") == "https://ghostarchive.org/archive/Exist1"
        mock_submit.assert_not_called()

    def test_enrich_submits_when_no_existing(self, mocker, make_item):
        """enrich() should submit URL when no existing archive found."""
        mocker.patch.object(self.enricher, "_search_existing", return_value=None)
        mocker.patch.object(self.enricher, "_submit_url", return_value="https://ghostarchive.org/archive/New42")

        item = make_item("https://example.com")
        result = self.enricher.enrich(item)

        assert result is True
        assert item.get("ghostarchive") == "https://ghostarchive.org/archive/New42"

    def test_enrich_skips_check_existing_when_disabled(self, mocker, make_item):
        """enrich() should skip search when check_existing is False."""
        self.enricher.check_existing = False
        mock_search = mocker.patch.object(self.enricher, "_search_existing")
        mocker.patch.object(self.enricher, "_submit_url", return_value="https://ghostarchive.org/archive/Direct1")

        item = make_item("https://example.com")
        result = self.enricher.enrich(item)

        assert result is True
        mock_search.assert_not_called()

    @pytest.mark.download
    def test_real_search_existing(self, setup_module):
        """Integration test: search for an existing archive on Ghost Archive."""
        enricher = setup_module("ghostarchive_enricher", ENRICHER_CONFIG)
        # example.com is commonly archived
        result = enricher._search_existing("https://example.com")
        # we just check it doesn't crash; result may or may not be found
        assert result is None or result.startswith("https://ghostarchive.org/archive/")

    @pytest.mark.download
    @pytest.mark.skipif(CI, reason="Avoid submitting a real task on every CI run")
    def test_real_submit_example_com(self, setup_module, make_item):
        """Integration test: submit example.com to Ghost Archive and verify enrichment."""
        enricher = setup_module("ghostarchive_enricher", ENRICHER_CONFIG)
        item = make_item("https://example.com")
        result = enricher.enrich(item)

        assert result is True
        archive_url = item.get("ghostarchive")
        assert archive_url is not None
        assert archive_url.startswith("https://ghostarchive.org/archive/")
