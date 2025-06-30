import os
from zipfile import ZipFile

import pytest

from auto_archiver.core import Metadata, Media
from auto_archiver.core.consts import SetupError


@pytest.fixture
def wacz_enricher(setup_module, mock_binary_dependencies):
    configs: dict = {
        "profile": None,
        "docker_commands": None,
        "timeout": 120,
        "extract_media": False,
        "extract_screenshot": True,
        "socks_proxy_host": None,
        "socks_proxy_port": None,
        "proxy_server": None,
    }
    wacz = setup_module("wacz_extractor_enricher", configs)
    return wacz


def test_raises_error_without_docker_installed(setup_module, mocker, caplog):
    # pretend that docker isn't installed
    mocker.patch("shutil.which").return_value = None
    with pytest.raises(SetupError):
        setup_module("wacz_extractor_enricher", {})

    assert "requires external dependency 'docker' which is not available/setup" in caplog.text


def test_setup_without_docker(wacz_enricher, mocker):
    mocker.patch.dict(os.environ, {"RUNNING_IN_DOCKER": "1"}, clear=True)
    wacz_enricher.setup()
    assert not wacz_enricher.docker_in_docker


def test_setup_with_docker(wacz_enricher, mocker):
    mocker.patch.dict(os.environ, {"WACZ_ENABLE_DOCKER": "1"}, clear=True)
    wacz_enricher.setup()
    assert wacz_enricher.use_docker


def test_already_ran(wacz_enricher, metadata, mocker):
    metadata.add_media(Media("test.wacz"), id="browsertrix")
    mock_log = mocker.patch("auto_archiver.utils.custom_logger.logger.info")
    assert wacz_enricher.enrich(metadata) is True
    assert "WACZ enricher had already been executed" in mock_log.call_args[0][0]


def test_basic_call_execution(wacz_enricher, mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0)
    metadata = Metadata().set_url("https://example.com")
    wacz_enricher.enrich(metadata)
    assert mock_run.called
    # Checks that the url is passed to the cmd
    assert "--url https://example.com" in " ".join(mock_run.call_args[0][0])


def test_download_success(wacz_enricher, mocker) -> None:
    """Test download returns metadata on successful enrichment."""
    basic_metadata = Metadata().set_url("https://example.com")
    mocker.patch.object(wacz_enricher, "enrich", return_value=True)
    result = wacz_enricher.download(basic_metadata)
    assert result is not None
    assert isinstance(result, Metadata)
    assert result.status == "wacz: success"


def test_enrich_already_executed(wacz_enricher, mocker) -> None:
    """Test enrich  if already executed."""
    mock_log = mocker.patch("auto_archiver.utils.custom_logger.logger.info")
    metadata = Metadata().set_url("https://example.com")
    media = Media(filename="some_file.wacz")
    metadata.add_media(media, id="browsertrix")
    result = wacz_enricher.enrich(metadata)
    assert result is True
    assert "WACZ enricher had already been executed:" in mock_log.call_args[0][0]


def test_enrich_subprocess_exception(wacz_enricher, mocker, tmp_path) -> None:
    """Test enrich returns False when subprocess fails."""
    wacz_enricher.tmp_dir = str(tmp_path)
    wacz_enricher.extract_media = False
    wacz_enricher.extract_screenshot = True
    mocker.patch("auto_archiver.utils.misc.random_str", return_value="TESTCOL")
    mocker.patch("subprocess.run", side_effect=Exception("fail"))
    basic_metadata = Metadata().set_url("https://example.com")
    result = wacz_enricher.enrich(basic_metadata)
    assert result is False


def test_extract_media(wacz_enricher, metadata, tmp_path, mocker) -> None:
    """Test extract_media_from_wacz extracts screenshot media."""
    wacz_enricher.tmp_dir = str(tmp_path)

    # Create a *real* zip file so ZipFile won't fail.
    wacz_file = tmp_path / "dummy.wacz"
    with ZipFile(wacz_file, "w") as zf:
        zf.writestr("dummy.txt", "test content")

    mocker.patch("os.listdir", return_value=[])
    warc_data = (
        b"WARC/1.0\r\n"
        b"WARC-Type: resource\r\n"
        b"Content-Type: image/png\r\n"
        b"WARC-Target-URI: http://example.com/image.png\r\n"
        b"Content-Length: 12\r\n"
        b"\r\n"
        b"image-bytes"
        b"\r\n\r\nWARC/1.0\r\n\r\n"
    )
    mock_file = mocker.mock_open(read_data=warc_data)
    mocker.patch("builtins.open", mock_file)
    metadata.add_media(Media("something.wacz"), "browsertrix")
    wacz_enricher.extract_media_from_wacz(metadata, str(wacz_file))
    assert len(metadata.media) == 2
    assert metadata.media[1].properties.get("id") == "browsertrix-screenshot-0"
