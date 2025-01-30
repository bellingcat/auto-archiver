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
        "username": {"required": True,
                     "help": "a valid Instagram username"},
        "password": {
            "required": True,
            "help": "the corresponding Instagram account password",
        },
        "download_folder": {
            "default": "instaloader",
            "help": "name of a folder to temporarily download content to",
        },
        "session_file": {
            "default": "secrets/instaloader.session",
            "help": "path to the instagram session which saves session credentials",
        },
        # TODO: fine-grain
        # "download_stories": {"default": True, "help": "if the link is to a user profile: whether to get stories information"},
    },
    "description": """
    Uses the [Instaloader library](https://instaloader.github.io/as-module.html) to download content from Instagram. This class handles both individual posts
    and user profiles, downloading as much information as possible, including images, videos, text, stories,
    highlights, and tagged posts. 
    Authentication is required via username/password or a session file.
                    
                    """,
}
