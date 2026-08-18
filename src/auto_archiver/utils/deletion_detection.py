"""
Deletion Detection Utilities

Provides a best-effort detection of deleted, missing, or unavailable content
across various social media platforms based on presence of expected keywords.

This module helps identify removed content, helps to:
- Document content that existed but was deleted
- Track patterns of content removal
- Preserve metadata about missing content
"""

from typing import Optional, Dict, List
from auto_archiver.utils.custom_logger import logger
from urllib.parse import urlparse


class DeletionIndicators:
    """
    Platform-specific indicators that content has been deleted or is unavailable, alongside generic indicators.
    """

    # Twitter/X deletion indicators
    TWITTER = [
        "Hmm...this page doesn't exist",
        "Try searching for something else",
        "This Tweet is unavailable",
        "This account doesn't exist",
        "This Tweet has been deleted",
        "This account has been suspended",
        "Sorry, that page doesn't exist",
        "The Tweet you're looking for isn't available",
    ]

    # Facebook deletion indicators
    FACEBOOK = [
        "This content isn't available",
        "Sorry, this content isn't available",
        "This content is no longer available",
        "The link you followed may be broken",
        "Page Not Found",
        "Content Not Found",
        "This content is no longer on Facebook",
    ]

    # Instagram deletion indicators
    INSTAGRAM = [
        "Sorry, this page isn't available",
        "The link you followed may be broken",
        "Media not found or unavailable",
        "This post is no longer available",
        "This account is private",
    ]

    # TikTok deletion indicators
    TIKTOK = [
        "Couldn't find this account",
        "This video is no longer available",
        "This video is currently unavailable",
        "Video not found",
        "This video may have been deleted",
    ]

    # YouTube deletion indicators
    YOUTUBE = [
        "This video isn't available anymore",
        "Video unavailable",
        "This video has been removed",
        "This video is no longer available",
        "This video is private",
        "This video has been removed by the uploader",
        "This video has been deleted",
    ]

    # Reddit deletion indicators
    REDDIT = [
        "this post has been removed",
        "this comment has been removed",
        "[removed]",
        "[deleted]",
        "page not found",
        "there doesn't seem to be anything here",
    ]

    # VK deletion indicators
    VK = [
        "Post deleted",
        "Page not found",
        "Content unavailable",
        "Access denied",
    ]

    # Telegram deletion indicators
    TELEGRAM = [
        "Message not found",
        "Deleted message",
        "Channel is private",
    ]

    # Generic indicators (work across platforms)
    GENERIC = [
        "has been removed",
        "no longer available",
        "content removed",
        "access denied",
        "page not found",
    ]

    @classmethod
    def all_indicators(cls) -> List[str]:
        """Returns all deletion indicators from all platforms."""
        return (
            cls.TWITTER
            + cls.FACEBOOK
            + cls.INSTAGRAM
            + cls.TIKTOK
            + cls.YOUTUBE
            + cls.REDDIT
            + cls.VK
            + cls.TELEGRAM
            + cls.GENERIC
        )

    @classmethod
    def for_url(cls, url: str) -> List[str]:
        """Returns platform-specific indicators based on URL domain."""
        platform = _extract_platform(url)

        indicators_map = {
            "twitter": cls.TWITTER + cls.GENERIC,
            "facebook": cls.FACEBOOK + cls.GENERIC,
            "instagram": cls.INSTAGRAM + cls.GENERIC,
            "tiktok": cls.TIKTOK + cls.GENERIC,
            "youtube": cls.YOUTUBE + cls.GENERIC,
            "reddit": cls.REDDIT + cls.GENERIC,
            "vk": cls.VK + cls.GENERIC,
            "telegram": cls.TELEGRAM + cls.GENERIC,
        }
        return indicators_map.get(platform, cls.GENERIC)


def detect_deletion(
    html_content: str = None,
    page_title: str = None,
    error_message: str = None,
    url: str = None,
    video_data: dict = None,
) -> Optional[Dict[str, any]]:
    """
    Best-effort deletion detection across multiple signals.

    Checks HTML content, page titles, error messages, and video metadata for
    indicators that content has been deleted or is unavailable.

    Args:
        html_content: Raw HTML source of the page
        page_title: Browser page title
        error_message: Any error message from the extractor
        url: The URL being archived (for platform-specific detection)
        video_data: Video metadata from yt-dlp or other extractors

    Returns:
        Dictionary with deletion details if detected, None otherwise.
        Format: {
            "is_deleted": True,
            "indicator": "specific text that was found",
            "source": "html|title|error|metadata",
            "platform": "twitter|facebook|etc"
        }
    """

    # Determine indicators to check based on URL
    if url:
        indicators = DeletionIndicators.for_url(url)
        platform = _extract_platform(url)
    else:
        indicators = DeletionIndicators.all_indicators()
        platform = "unknown"

    # Check HTML content
    if html_content:
        for indicator in indicators:
            if indicator.lower() in html_content.lower():
                logger.info(f"Deletion detected in HTML: '{indicator}' found for {url}")
                return {"is_deleted": True, "indicator": indicator, "source": "html_content", "platform": platform}

    # Check page title
    if page_title:
        for indicator in indicators:
            if indicator.lower() in page_title.lower():
                logger.info(f"Deletion detected in page title: '{indicator}' found for {url}")
                return {"is_deleted": True, "indicator": indicator, "source": "page_title", "platform": platform}

    # Check error messages
    if error_message:
        for indicator in indicators:
            if indicator.lower() in str(error_message).lower():
                logger.info(f"Deletion detected in error: '{indicator}' found for {url}")
                return {"is_deleted": True, "indicator": indicator, "source": "error_message", "platform": platform}

    # Check video metadata (from yt-dlp)
    if video_data:
        # Check if yt-dlp flagged it as unavailable
        if video_data.get("availability") in ["unavailable", "private", "deleted"]:
            logger.info(f"Deletion detected in metadata: availability={video_data.get('availability')}")
            return {
                "is_deleted": True,
                "indicator": f"availability: {video_data.get('availability')}",
                "source": "video_metadata",
                "platform": platform,
            }

        # Check description/title for deletion indicators
        for key in ["title", "description", "fulltitle"]:
            if key in video_data:
                for indicator in indicators:
                    if indicator.lower() in str(video_data[key]).lower():
                        logger.info(f"Deletion detected in {key}: '{indicator}'")
                        return {
                            "is_deleted": True,
                            "indicator": indicator,
                            "source": f"video_metadata_{key}",
                            "platform": platform,
                        }

    return None


def _extract_platform(url: str) -> str:
    """Extracts platform name from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc

    if "twitter.com" in domain or "x.com" in domain:
        return "twitter"
    elif "facebook.com" in domain or "fb.com" in domain:
        return "facebook"
    elif "instagram.com" in domain:
        return "instagram"
    elif "tiktok.com" in domain:
        return "tiktok"
    elif "youtube.com" in domain or "youtu.be" in domain:
        return "youtube"
    elif "reddit.com" in domain:
        return "reddit"
    elif "vk.com" in domain:
        return "vk"
    elif "t.me" in domain:
        return "telegram"
    return "unknown"


def flag_as_deleted(metadata, deletion_info: Dict[str, any]) -> None:
    """
    Flags metadata object as deleted/unavailable.
    Adds tentative deletion information to the metadata object.

    Args:
        metadata: Metadata object to update
        deletion_info: Dictionary from detect_deletion()
    """
    metadata.set("deletion_detected", True)
    metadata.set("deletion_indicator", deletion_info.get("indicator"))
    metadata.set("deletion_source", deletion_info.get("source"))
    metadata.set("deletion_platform", deletion_info.get("platform"))
    metadata.status = "deleted_or_unavailable"

    logger.debug(
        f"Content marked as deleted/unavailable: "
        f"platform={deletion_info.get('platform')}, "
        f"indicator='{deletion_info.get('indicator')}', "
        f"source={deletion_info.get('source')}"
    )
