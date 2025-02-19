import base64

import pytest
from selenium.common.exceptions import TimeoutException

from auto_archiver.core import Metadata, Media
from auto_archiver.modules.screenshot_enricher import ScreenshotEnricher


@pytest.fixture
def mock_selenium_env(mocker):
    """Patches Selenium calls and driver checks in one place."""

    # Patch external dependencies
    mock_which = mocker.patch("shutil.which")
    mock_driver_class = mocker.patch("auto_archiver.utils.webdriver.CookieSettingDriver")
    mock_binary_paths = mocker.patch("selenium.webdriver.common.selenium_manager.SeleniumManager.binary_paths")
    mock_is_file = mocker.patch("pathlib.Path.is_file", return_value=True)
    mock_popen = mocker.patch("subprocess.Popen")
    mock_is_connectable = mocker.patch("selenium.webdriver.common.service.Service.is_connectable", return_value=True)
    mock_firefox_options = mocker.patch("selenium.webdriver.FirefoxOptions")
    # Define side effect for `shutil.which`
    def mock_which_side_effect(dep):
        return "/mock/geckodriver" if dep == "geckodriver" else None
    mock_which.side_effect = mock_which_side_effect

    # Mock binary paths
    mock_binary_paths.return_value = {
        "driver_path": "/mock/driver",
        "browser_path": "/mock/browser",
    }
    # Mock `subprocess.Popen`
    mock_proc = mocker.MagicMock()
    mock_proc.poll.return_value = None
    mock_popen.return_value = mock_proc
    # Mock `CookieSettingDriver`
    mock_driver = mocker.MagicMock()
    mock_driver_class.return_value = mock_driver
    # Mock `FirefoxOptions`
    mock_options_instance = mocker.MagicMock()
    mock_firefox_options.return_value = mock_options_instance
    yield mock_driver, mock_driver_class, mock_options_instance


@pytest.fixture
def common_patches(tmp_path, mocker):
    """Patches common utilities used across multiple tests."""
    mocker.patch("auto_archiver.utils.url.is_auth_wall", return_value=False)
    mocker.patch("os.path.join", return_value=str(tmp_path / "test.png"))
    mocker.patch("time.sleep")
    yield


@pytest.fixture
def screenshot_enricher(setup_module, mock_binary_dependencies) -> ScreenshotEnricher:
    configs: dict = {
        "width": 1280,
        "height": 720,
        "timeout": 60,
        "sleep_before_screenshot": 4,
        "http_proxy": "",
        "save_to_pdf": "False",
        "print_options": {},
    }
    return setup_module("screenshot_enricher", configs)


@pytest.fixture
def metadata_with_video():
    m = Metadata()
    m.set_url("https://example.com")
    m.add_media(Media(filename="video.mp4").set("id", "video1"))
    return m


def test_enrich_adds_screenshot(
    screenshot_enricher,
    metadata_with_video,
    mock_selenium_env,
    common_patches,
    tmp_path,
):
    mock_driver, mock_driver_class, mock_options_instance = mock_selenium_env
    screenshot_enricher.enrich(metadata_with_video)
    mock_driver_class.assert_called_once_with(
        cookies=None,
        cookiejar=None,
        facebook_accept_cookies=False,
        options=mock_options_instance,
    )
    # Verify the actual calls on the returned mock_driver
    mock_driver.get.assert_called_once_with("https://example.com")
    mock_driver.save_screenshot.assert_called_once_with(str(tmp_path / "test.png"))
    # Check that the media was added (2 = original video + screenshot)
    assert len(metadata_with_video.media) == 2
    assert metadata_with_video.media[1].properties.get("id") == "screenshot"


@pytest.mark.parametrize(
    "url,is_auth",
    [
        ("https://example.com", False),
        ("https://private.com", True),
    ],
)
def test_enrich_auth_wall(
    screenshot_enricher,
    metadata_with_video,
    mock_selenium_env,
    common_patches,
    url,
    is_auth,
    mocker
):
    # Testing with and without is_auth_wall
    mock_driver, mock_driver_class, _ = mock_selenium_env
    mocker.patch("auto_archiver.utils.url.is_auth_wall", return_value=is_auth)
    metadata_with_video.set_url(url)
    screenshot_enricher.enrich(metadata_with_video)

    if is_auth:
        mock_driver.get.assert_not_called()
        assert len(metadata_with_video.media) == 1
        assert metadata_with_video.media[0].properties.get("id") == "video1"
    else:
        mock_driver.get.assert_called_once_with(url)
        assert len(metadata_with_video.media) == 2
        assert metadata_with_video.media[1].properties.get("id") == "screenshot"


def test_handle_timeout_exception(
    screenshot_enricher, metadata_with_video, mock_selenium_env, mocker
):
    mock_driver, mock_driver_class, mock_options_instance = mock_selenium_env

    mock_driver.get.side_effect = TimeoutException
    mock_log = mocker.patch("loguru.logger.info")
    screenshot_enricher.enrich(metadata_with_video)
    mock_log.assert_called_once_with("TimeoutException loading page for screenshot")
    assert len(metadata_with_video.media) == 1


def test_handle_general_exception(
    screenshot_enricher, metadata_with_video, mock_selenium_env, mocker
):
    """Test proper handling of unexpected general exceptions"""
    mock_driver, mock_driver_class, mock_options_instance = mock_selenium_env
    # Simulate a generic exception when save_screenshot is called
    mock_driver.get.return_value = None
    mock_driver.save_screenshot.side_effect = Exception("Unexpected Error")

    mock_log = mocker.patch("loguru.logger.error")
    screenshot_enricher.enrich(metadata_with_video)
    # Verify that the exception was logged with the log
    mock_log.assert_called_once_with(
        "Got error while loading webdriver for screenshot enricher: Unexpected Error"
    )
    # And no new media was added due to the error
    assert len(metadata_with_video.media) == 1


def test_pdf_creation(mocker, screenshot_enricher, metadata_with_video, mock_selenium_env):
    """Test PDF creation when save_to_pdf is enabled"""
    mock_driver, mock_driver_class, mock_options_instance = mock_selenium_env
    # Override the save_to_pdf option
    screenshot_enricher.save_to_pdf = True
    # Mock the print_page method to return base64-encoded content
    mock_driver.print_page.return_value = base64.b64encode(b"fake_pdf_content").decode("utf-8")
    # Patch functions with mocker
    mock_os_path_join = mocker.patch("os.path.join", side_effect=lambda *args: f"{args[-1]}")
    mock_random_str = mocker.patch(
        "auto_archiver.modules.screenshot_enricher.screenshot_enricher.random_str",
        return_value="fixed123",
    )
    mock_open = mocker.patch("builtins.open", new_callable=mocker.mock_open)
    mock_log_error = mocker.patch("loguru.logger.error")

    screenshot_enricher.enrich(metadata_with_video)
    # Verify screenshot and PDF creation
    mock_driver.save_screenshot.assert_called_once()
    mock_driver.print_page.assert_called_once_with(mock_driver.print_options)
    # Check that PDF file was opened and written
    mock_open.assert_any_call("pdf_fixed123.pdf", "wb")

    # Ensure both screenshot and PDF were added as media
    assert len(metadata_with_video.media) == 3
    assert metadata_with_video.media[1].properties.get("id") == "screenshot"
    assert metadata_with_video.media[2].properties.get("id") == "pdf"


@pytest.fixture(autouse=True)
def cleanup_files(tmp_path):
    yield
    for file in tmp_path.iterdir():
        file.unlink()
