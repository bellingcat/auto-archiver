import pytest
from auto_archiver.utils.url import (
    is_auth_wall,
    check_url_or_raise,
    domain_for_url,
    is_relevant_url,
    remove_get_parameters,
    twitter_best_quality_url,
)


@pytest.mark.parametrize(
    "url, is_auth",
    [
        ("https://example.com", False),
        ("https://t.me/c/abc/123", True),
        ("https://t.me/not-private/", False),
        ("https://instagram.com", True),
        ("https://www.instagram.com", True),
        ("https://www.instagram.com/p/INVALID", True),
        ("https://www.instagram.com/p/C4QgLbrIKXG/", True),
    ],
)
def test_is_auth_wall(url, is_auth):
    assert is_auth_wall(url) == is_auth


@pytest.mark.parametrize(
    "url, raises",
    [
        ("http://example.com", False),
        ("https://example.com", False),
        ("ftp://example.com", True),
        ("http://localhost", True),
        ("http://", True),
    ],
)
def test_check_url_or_raise(url, raises):
    if raises:
        with pytest.raises(ValueError):
            check_url_or_raise(url)
    else:
        assert check_url_or_raise(url)


@pytest.mark.parametrize(
    "url, domain",
    [
        ("https://example.com", "example.com"),
        ("https://www.example.com", "www.example.com"),
        ("https://www.example.com/path", "www.example.com"),
        ("https://", ""),
        ("http://localhost", "localhost"),
    ],
)
def test_domain_for_url(url, domain):
    assert domain_for_url(url) == domain


@pytest.mark.parametrize(
    "url, without_get",
    [
        ("https://example.com", "https://example.com"),
        ("https://example.com?utm_source=example", "https://example.com"),
        ("https://example.com?utm_source=example&other=1", "https://example.com"),
        ("https://example.com/something", "https://example.com/something"),
        ("https://example.com/something?utm_source=example", "https://example.com/something"),
    ],
)
def test_remove_get_parameters(url, without_get):
    assert remove_get_parameters(url) == without_get


@pytest.mark.parametrize(
    "url, relevant",
    [
        ("https://example.com", True),
        ("https://example.com/favicon.ico", False),
        ("https://twimg.com/profile_images", False),
        ("https://twimg.com/something/default_profile_images", False),
        ("https://scontent.cdninstagram.com/username/150x150.jpg", False),
        ("https://static.cdninstagram.com/rsrc.php/", False),
        ("https://telegram.org/img/emoji/", False),
        ("https://www.youtube.com/s/gaming/emoji/", False),
        ("https://yt3.ggpht.com/default-user=", False),
        ("https://www.youtube.com/s/search/audio/", False),
        ("https://ok.ru/res/i/", False),
        ("https://vk.com/emoji/", False),
        ("https://vk.com/images/", False),
        ("https://vk.com/images/reaction/", False),
        ("https://wikipedia.org/static", False),
        ("https://example.com/file.svg", False),
        ("https://example.com/file.ico", False),
        ("https://example.com/file.mp4", True),
        ("https://example.com/150x150.jpg", True),
        ("https://example.com/rsrc.php/", True),
        ("https://example.com/img/emoji/", True),
    ],
)
def test_is_relevant_url(url, relevant):
    assert is_relevant_url(url) == relevant


@pytest.mark.parametrize(
    "url, best_quality",
    [
        ("https://twitter.com/some_image.jpg?name=small", "https://twitter.com/some_image.jpg?name=orig"),
        ("https://twitter.com/some_image.jpg", "https://twitter.com/some_image.jpg"),
        ("https://twitter.com/some_image.jpg?name=orig", "https://twitter.com/some_image.jpg?name=orig"),
    ],
)
def test_twitter_best_quality_url(url, best_quality):
    assert twitter_best_quality_url(url) == best_quality
