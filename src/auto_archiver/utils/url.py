import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from ipaddress import ip_address


AUTHWALL_URLS = [
    re.compile(r"https?:\/\/t\.me(\/c)\/(.+)\/(\d+)"),  # telegram private channels
    re.compile(r"https?:\/\/(www\.)?instagram\.com"),  # instagram
]


def check_url_or_raise(url: str) -> bool | ValueError:
    """
    Blocks localhost, private, reserved, and link-local IPs and all non-http/https schemes.
    """

    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError(f"Invalid URL scheme for url {url}")

    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError(f"Invalid URL hostname for url {url}")

    if parsed.hostname == "localhost":
        raise ValueError(f"Localhost URLs cannot be parsed for security reasons (for url {url})")

    if parsed.scheme not in ["http", "https"]:
        raise ValueError(f"Invalid URL scheme, only http and https supported (for url {url})")

    try:  # special rules for IP addresses
        ip = ip_address(parsed.hostname)
    except ValueError:
        pass

    else:
        if not ip.is_global:
            raise ValueError(f"IP address {ip} is not globally reachable")
        if ip.is_reserved:
            raise ValueError(f"Reserved IP address {ip} used")
        if ip.is_link_local:
            raise ValueError(f"Link-local IP address {ip} used")
        if ip.is_private:
            raise ValueError(f"Private IP address {ip} used")

    return True


def domain_for_url(url: str) -> str:
    """
    SECURITY: parse the domain using urllib to avoid any potential security issues
    """
    return urlparse(url).netloc


def clean(url: str) -> str:
    TRACKERS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}

    parsed = urlparse(url)
    clean_qs = [(k, v) for k, v in parse_qsl(parsed.query) if k not in TRACKERS]
    return parsed._replace(query=urlencode(clean_qs)).geturl()


def is_auth_wall(url: str) -> bool:
    """
    checks if URL is behind an authentication wall meaning steps like wayback, wacz, ... may not work
    """
    for regex in AUTHWALL_URLS:
        if regex.match(url):
            return True

    return False


def remove_get_parameters(url: str) -> str:
    # http://example.com/file.mp4?t=1 -> http://example.com/file.mp4
    # useful for mimetypes to work
    parsed_url = urlparse(url)
    new_url = urlunparse(parsed_url._replace(query=""))
    return new_url


def is_relevant_url(url: str) -> bool:
    """
    Detect if a detected media URL is recurring and therefore irrelevant to a specific archive. Useful, for example, for the enumeration of the media files in WARC files which include profile pictures, favicons, etc.

    Assumption: URLs are relevant if they refer to files that can be downloaded with curl/requests, so excludes extensions like .m3u8.
    """
    clean_url = remove_get_parameters(url)

    IRRELEVANT_URLS = [
        # favicons
        ("favicon",),
        # twitter profile pictures
        ("twimg.com/profile_images",),
        ("twimg.com", "default_profile_images"),
        # instagram profile pictures
        ("https://scontent.cdninstagram.com/", "150x150"),
        # instagram recurring images
        ("https://static.cdninstagram.com/rsrc.php/",),
        # telegram
        ("https://telegram.org/img/emoji/",),
        # youtube
        ("https://www.youtube.com/s/gaming/emoji/",),
        ("https://yt3.ggpht.com", "default-user="),
        ("https://www.youtube.com/s/search/audio/",),
        # ok
        ("https://ok.ru/res/i/",),
        ("https://vk.com/emoji/",),
        ("vk.com/images/",),
        ("vk.com/images/reaction/",),
        # wikipedia
        ("wikipedia.org/static",),
        # reddit
        ("styles.redditmedia.com",),  # opinionated but excludes may irrelevant images like avatars and banners
        ("emoji.redditmedia.com",),
        # linkedin
        ("static.licdn.com",),
    ]

    # TODO: make these globally configurable
    IRRELEVANT_ENDS_WITH = [
        ".svg",  # ignore SVGs
        ".ico",  # ignore icons
        # ignore index files for videos, these should be handled by ytdlp
        ".m3u8",
        ".mpd",
        ".ism",
    ]

    for end in IRRELEVANT_ENDS_WITH:
        if clean_url.endswith(end):
            return False

    for parts in IRRELEVANT_URLS:
        if all(part in clean_url for part in parts):
            return False

    return True


def twitter_best_quality_url(url: str) -> str:
    """
    some twitter image URLs point to a less-than best quality
    this returns the URL pointing to the highest (original) quality (with 'name=orig')
    """
    parsed = urlparse(url)
    query = parsed.query
    if "name=" in query:
        # Replace only the first occurrence of name=xxx with name=orig
        new_query = re.sub(r"name=[^&]*", "name=orig", query, 1)
        parsed = parsed._replace(query=new_query)
        return urlunparse(parsed)
    return url


def get_media_url_best_quality(url: str) -> str:
    """
    Returns the best quality URL for the given media URL, it may not exist.
    """
    parsed = urlparse(url)

    # twitter case
    if any(d in parsed.netloc.replace("www", "") for d in ("twitter.com", "twimg.com", "x.com")):
        url = twitter_best_quality_url(url)
        parsed = urlparse(url)

    # some cases https://example.com/media-1280x720.mp4 to https://example.com/media.mp4
    basename = parsed.path.split("/")[-1]
    match = re.match(r"(.+)-\d+x\d+(\.[a-zA-Z0-9]+)$", basename)
    if match:
        orig_basename = match.group(1) + match.group(2)
        new_path = "/".join(parsed.path.split("/")[:-1] + [orig_basename])
        parsed = parsed._replace(path=new_path)  # keep the query unchanged
        url = urlunparse(parsed)

    return url
