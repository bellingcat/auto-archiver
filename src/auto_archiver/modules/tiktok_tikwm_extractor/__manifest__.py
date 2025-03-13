{
    "name": "Tiktok Tikwm Extractor",
    "type": ["extractor"],
    "requires_setup": False,
    "dependencies": {"python": ["loguru", "requests"], "bin": []},
    "description": """
    Uses an unofficial TikTok video download platform's API to download videos: https://tikwm.com/
	
	This extractor complements the generic_extractor which can already get TikTok videos, but this one can extract special videos like those marked as sensitive.

    ### Features
    - Downloads the video and, if possible, also the video cover.
	- Stores extra metadata about the post like author information, and more as returned by tikwm.com. 

    ### Notes
    - If tikwm.com is down, this extractor will not work.
	- If tikwm.com changes their API, this extractor may break.
	- If no video is found, this extractor will consider the extraction failed.
    """,
}
