import pytest
from auto_archiver.utils.url import (
    clean,
    is_auth_wall,
    check_url_or_raise,
    domain_for_url,
    is_relevant_url,
    remove_get_parameters,
    twitter_best_quality_url,
    get_media_url_best_quality,
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
        ("https://styles.redditmedia.com/123", False),
        ("https://emoji.redditmedia.com/abc.jpg", False),
        ("https://example.com/rsrc.m3u8?asdasd=10", False),
        ("https://example.com/rsrc.mpd", False),
        ("https://example.com/rsrc.ism?vid=12", False),
    ],
)
def test_is_relevant_url(url, relevant):
    assert is_relevant_url(url) == relevant


@pytest.mark.parametrize(
    "url, best_quality",
    [
        (
            "https://twitter.com/some_image.jpg?name=small&this_is_another=145",
            "https://twitter.com/some_image.jpg?name=orig&this_is_another=145",
        ),
        ("https://twitter.com/some_image.jpg", "https://twitter.com/some_image.jpg"),
        ("https://twitter.com/some_image.jpg?name=orig", "https://twitter.com/some_image.jpg?name=orig"),
    ],
)
def test_twitter_best_quality_url(url, best_quality):
    assert twitter_best_quality_url(url) == best_quality


@pytest.mark.parametrize(
    "input_url,expected_url",
    [
        # Twitter: add/replace name= to name=orig
        (
            "https://pbs.twimg.com/media/abc123?format=jpg&name=small",
            "https://pbs.twimg.com/media/abc123?format=jpg&name=orig",
        ),
        ("https://pbs.twimg.com/media/abc123?name=large", "https://pbs.twimg.com/media/abc123?name=orig"),
        ("https://pbs.twimg.com/media/abc123?format=jpg", "https://pbs.twimg.com/media/abc123?format=jpg"),
        # Twitter: already orig
        (
            "https://pbs.twimg.com/media/abc123?format=jpg&name=orig",
            "https://pbs.twimg.com/media/abc123?format=jpg&name=orig",
        ),
        # X.com domain
        ("https://x.com/media/abc123?name=medium", "https://x.com/media/abc123?name=orig"),
        # twimg.com domain
        ("https://twimg.com/media/abc123?name=thumb", "https://twimg.com/media/abc123?name=orig"),
        # Non-twitter domain, no change
        ("https://example.com/media/file.mp4", "https://example.com/media/file.mp4"),
        # Remove -WxH from basename
        ("https://example.com/media/file-1280x720.mp4", "https://example.com/media/file.mp4"),
        ("https://example.com/media/file-1920x1080.jpg?foo=bar", "https://example.com/media/file.jpg?foo=bar"),
        # Both twitter and -WxH
        ("https://pbs.twimg.com/media/abc-1280x720.jpg?name=small", "https://pbs.twimg.com/media/abc.jpg?name=orig"),
        # No match for -WxH, no change
        ("https://example.com/media/file.mp4?foo=bar", "https://example.com/media/file.mp4?foo=bar"),
        # Path with multiple directories
        ("https://example.com/a/b/c/file-640x480.png", "https://example.com/a/b/c/file.png"),
        # -WxH in directory, not basename (should not change)
        ("https://example.com/media-1280x720/file.mp4", "https://example.com/media-1280x720/file.mp4"),
    ],
)
def test_get_media_url_best_quality(input_url, expected_url):
    assert get_media_url_best_quality(input_url) == expected_url


@pytest.mark.parametrize(
    "input_url,expected_url",
    [
        # No trackers present
        ("https://example.com/page?foo=bar&baz=qux", "https://example.com/page?foo=bar&baz=qux"),
        # Single tracker present
        ("https://example.com/page?utm_source=google&foo=bar", "https://example.com/page?foo=bar"),
        # Multiple trackers present
        ("https://example.com/page?utm_source=google&utm_medium=email&utm_campaign=spring", "https://example.com/page"),
        # Trackers mixed with other params
        (
            "https://example.com/page?foo=bar&utm_content=abc&baz=qux&gclid=123",
            "https://example.com/page?foo=bar&baz=qux",
        ),
        # Only trackers present
        ("https://example.com/page?utm_source=google&gclid=123", "https://example.com/page"),
        # No query string
        ("https://example.com/page", "https://example.com/page"),
        # Trackers in fragment (should not be removed)
        ("https://example.com/page#utm_source=google", "https://example.com/page#utm_source=google"),
        # Trackers after fragment
        ("https://example.com/page?utm_source=google#section-1", "https://example.com/page#section-1"),
        # Trackers with empty value
        ("https://example.com/page?utm_source=&foo=bar", "https://example.com/page?foo=bar"),
        # Trackers with multiple values
        ("https://example.com/page?utm_source=google&utm_source=bing&foo=bar", "https://example.com/page?foo=bar"),
        # Trackers with encoded values
        ("https://example.com/page?utm_source=google%20ads&foo=bar", "https://example.com/page?foo=bar"),
        # Unrelated param with similar name
        ("https://example.com/page?utm_sourc=keepme&foo=bar", "https://example.com/page?utm_sourc=keepme&foo=bar"),
    ],
)
def test_clean_removes_trackers(input_url, expected_url):
    assert clean(input_url) == expected_url
