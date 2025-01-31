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
        "api_id": {
            "required": True,
            "help": "telegram API_ID value, go to https://my.telegram.org/apps",
        },
        "api_hash": {
            "required": True,
            "help": "telegram API_HASH value, go to https://my.telegram.org/apps",
        },
        "session_file": {
            "default": "secrets/anon-insta",
            "help": "optional, records the telegram login session for future usage, '.session' will be appended to the provided value.",
        },
        "timeout": {
            "default": 45,
            "type": "int",
            "help": "timeout to fetch the instagram content in seconds.",
        },
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
- Create your first session file using the script: `scripts/telegram_setup.py`
- You may need to enter your Telegram credentials (phone) and use the a 2FA code sent to you the first time you run the extractor.:
- A unique session file is then automatically created for each instance of the extractor to ensure secure access.
```
    """,
}
