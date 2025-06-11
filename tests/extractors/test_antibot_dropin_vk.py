import pytest
from auto_archiver.modules.antibot_extractor_enricher.dropins.vk import VkDropin


@pytest.mark.parametrize(
    "input_url,expected",
    [
        # Unrelated URL, should return unchanged
        (
            "https://vk.com/id123456",
            "https://vk.com/id123456",
        ),
        (
            "https://example.com/",
            "https://example.com/",
        ),
        # Wall post modal URL
        (
            "https://vk.com/somepage?w=wall-123456_7890",
            "https://vk.com/wall-123456_7890",
        ),
        # Wall post modal URL with no dash
        (
            "https://vk.com/somepage?w=wall123456_7890",
            "https://vk.com/wall123456_7890",
        ),
        # Photo modal URL
        (
            "https://vk.com/somepage?w=photo-654321_9876",
            "https://vk.com/photo-654321_9876",
        ),
        # Photo modal URL with no dash
        (
            "https://vk.com/somepage?w=photo654321_9876",
            "https://vk.com/photo654321_9876",
        ),
        # Video modal URL
        (
            "https://vk.com/somepage?w=video-111222_3334",
            "https://vk.com/video-111222_3334",
        ),
        # Video modal URL with extra part
        (
            "https://vk.com/somepage?w=video-111222_3334_ABC",
            "https://vk.com/video-111222_3334_ABC",
        ),
        # Video modal URL with no dash
        (
            "https://vk.com/somepage?w=video111222_3334",
            "https://vk.com/video111222_3334",
        ),
        # No modal, should return unchanged
        (
            "https://vk.com/wall-123456_7890",
            "https://vk.com/wall-123456_7890",
        ),
        (
            "https://vk.com/photo-654321_9876",
            "https://vk.com/photo-654321_9876",
        ),
        (
            "https://vk.com/video-111222_3334",
            "https://vk.com/video-111222_3334",
        ),
        # Clip modal URL
        (
            "https://vk.com/somepage?w=clip-555666_7778",
            "https://vk.com/clip-555666_7778",
        ),
        # Clip modal URL with no dash
        (
            "https://vk.com/somepage?w=clip555666_7778",
            "https://vk.com/clip555666_7778",
        ),
        # Clip modal URL with extra part
        (
            "https://vk.com/somepage?w=clip-555666_7778_ABC",
            "https://vk.com/clip-555666_7778",
        ),
        # No modal, should return unchanged (clip)
        (
            "https://vk.com/clip-555666_7778",
            "https://vk.com/clip-555666_7778",
        ),
        # Modal with multiple params, should still work with right priority
        (
            "https://vk.com/somepage?z=photo-654321_9876&w=wall-123456_7890",
            "https://vk.com/wall-123456_7890",
        ),
        (
            "https://vk.com/somepage?z=photo-654321_9876&w=video-111222_3334",
            "https://vk.com/video-111222_3334",
        ),
        (
            "https://vk.com/somepage?z=video-111222_3334&w=wall-654321_9876",
            "https://vk.com/wall-654321_9876",
        ),
    ],
)
def test_sanitize_url(input_url, expected):
    assert VkDropin.sanitize_url(input_url) == expected
