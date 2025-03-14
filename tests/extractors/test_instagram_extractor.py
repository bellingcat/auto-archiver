import pytest

from auto_archiver.modules.instagram_extractor import InstagramExtractor


@pytest.fixture
def instagram_extractor(setup_module, mocker):
    extractor_module: str = "instagram_extractor"
    config: dict = {
        "username": "user_name",
        "password": "password123",
        "download_folder": "instaloader",
        "session_file": "secrets/instaloader.session",
    }
    fake_loader = mocker.MagicMock()
    fake_loader.load_session_from_file.return_value = None
    fake_loader.login.return_value = None
    fake_loader.save_session_to_file.return_value = None
    mocker.patch(
        "instaloader.Instaloader",
        return_value=fake_loader,
    )
    return setup_module(extractor_module, config)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.instagram.com/p/",
        "https://www.instagram.com/p/1234567890/",
        "https://www.instagram.com/reel/1234567890/",
        "https://www.instagram.com/username/",
        "https://www.instagram.com/username/stories/",
        "https://www.instagram.com/username/highlights/",
    ],
)
def test_regex_matches(url: str, instagram_extractor: InstagramExtractor) -> None:
    """
    Ensure that the valid_url regex matches all provided Instagram URLs.
    """
    assert instagram_extractor.valid_url.match(url)
