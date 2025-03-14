{
    "name": "Instagram Telegram Bot Extractor",
    "type": ["extractor"],
    "dependencies": {
        "python": [
            "loguru",
            "telethon",
        ],
    },
    "requires_setup": True,
    "configs": {
        "api_id": {"default": None, "help": "telegram API_ID value, go to https://my.telegram.org/apps"},
        "api_hash": {"default": None, "help": "telegram API_HASH value, go to https://my.telegram.org/apps"},
        "session_file": {
            "default": "secrets/anon-insta",
            "help": "optional, records the telegram login session for future usage, '.session' will be appended to the provided value.",
        },
        "timeout": {"default": 45, "type": "int", "help": "timeout to fetch the instagram content in seconds."},
    },
    "description": """
The `InstagramTbotExtractor` module uses a Telegram bot (`instagram_load_bot`) to fetch and archive Instagram content,
such as posts and stories. It leverages the Telethon library to interact with the Telegram API, sending Instagram URLs
to the bot and downloading the resulting media and metadata. The downloaded content is stored as `Media` objects and
returned as part of a `Metadata` object.

### Features
- Supports archiving Instagram posts and stories through the Telegram bot.
- Downloads and saves media files (e.g., images, videos) in a temporary directory.
- Captures and returns metadata, including titles and descriptions, as a `Metadata` object.
- Automatically manages Telegram session files for secure access.

### Setup

To use the `InstagramTbotExtractor`, you need to provide the following configuration settings:
- **API ID and Hash**: Telegram API credentials obtained from [my.telegram.org/apps](https://my.telegram.org/apps).
- **Session File**: Optional path to store the Telegram session file for future use.
- The session file is created automatically and should be unique for each instance.
- You may need to enter your Telegram credentials (phone) and use the a 2FA code sent to you the first time you run the extractor.:
```2025-01-30 00:43:49.348 | INFO     | auto_archiver.modules.instagram_tbot_extractor.instagram_tbot_extractor:setup:36 - SETUP instagram_tbot_extractor checking login...
Please enter your phone (or bot token): +447123456789
Please enter the code you received: 00000
Signed in successfully as E C; remember to not break the ToS or you will risk an account ban!
```
    """,
}
