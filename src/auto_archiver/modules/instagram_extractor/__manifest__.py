{
    "name": "Instagram Extractor",
    "type": ["extractor"],
    "dependencies": {
        "python": [
            "instaloader",
            "loguru",
        ],
    },
    "requires_setup": True,
    "configs": {
        "username": {"required": True, "help": "A valid Instagram username."},
        "password": {
            "required": True,
            "help": "The corresponding Instagram account password.",
        },
        "download_folder": {
            "default": "instaloader",
            "help": "Name of a folder to temporarily download content to.",
        },
        "session_file": {
            "default": "secrets/instaloader.session",
            "help": "Path to the instagram session file which saves session credentials. If one doesn't exist this gives the path to store a new one.",
        },
        # TODO: fine-grain
        # "download_stories": {"default": True, "help": "if the link is to a user profile: whether to get stories information"},
    },
    "description": """
    Uses the [Instaloader library](https://instaloader.github.io/as-module.html) to download content from Instagram. 
    
      > ⚠️ **Warning**  
      > This module is not actively maintained due to known issues with blocking.  
      > Prioritise usage of the [Instagram Tbot Extractor](./instagram_tbot_extractor.md) and [Instagram API Extractor](./instagram_api_extractor.md)
  
    This class handles both individual posts and user profiles, downloading as much information as possible, including images, videos, text, stories,
    highlights, and tagged posts. 
    Authentication is required via username/password or a session file.
                    
                    """,
}
