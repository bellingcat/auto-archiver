import re
from urllib.parse import urlparse, urlunparse


AUTHWALL_URLS = [
    re.compile(r"https:\/\/t\.me(\/c)\/(.+)\/(\d+)"), # telegram private channels
    re.compile(r"https:\/\/www\.instagram\.com"), # instagram
]

def domain_for_url(url: str) -> str:
    """
    SECURITY: parse the domain using urllib to avoid any potential security issues
    """
    return urlparse(url).netloc

def clean(url: str) -> str:
    return url

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
    new_url = urlunparse(parsed_url._replace(query=''))
    return new_url

def is_relevant_url(url: str) -> bool:
    """
    Detect if a detected media URL is recurring and therefore irrelevant to a specific archive. Useful, for example, for the enumeration of the media files in WARC files which include profile pictures, favicons, etc.
    """
    clean_url = remove_get_parameters(url)

    # favicons
    if "favicon" in url: return False
    # ifnore icons
    if clean_url.endswith(".ico"): return False
    # ignore SVGs
    if remove_get_parameters(url).endswith(".svg"): return False

    # twitter profile pictures
    if "twimg.com/profile_images" in url: return False
    if "twimg.com" in url and "/default_profile_images" in url: return False

    # instagram profile pictures
    if "https://scontent.cdninstagram.com/" in url and "150x150" in url: return False
    # instagram recurring images
    if "https://static.cdninstagram.com/rsrc.php/" in url: return False

    # telegram
    if "https://telegram.org/img/emoji/" in url: return False

    # youtube
    if "https://www.youtube.com/s/gaming/emoji/" in url: return False
    if "https://yt3.ggpht.com" in url and "default-user=" in url: return False
    if "https://www.youtube.com/s/search/audio/" in url: return False

    # ok
    if " https://ok.ru/res/i/" in url: return False

    # vk
    if "https://vk.com/emoji/" in url: return False
    if "vk.com/images/" in url: return False
    if "vk.com/images/reaction/" in url: return False

    # wikipedia
    if "wikipedia.org/static" in url: return False

    return True

def twitter_best_quality_url(url: str) -> str:
    """
    some twitter image URLs point to a less-than best quality
    this returns the URL pointing to the highest (original) quality
    """
    return re.sub(r"name=(\w+)", "name=orig", url, 1)
