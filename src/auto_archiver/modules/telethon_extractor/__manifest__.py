{
    "name": "Telethon Extractor",
    "type": ["extractor"],
    "requires_setup": True,
    "dependencies": {
        "python": [
            "telethon",
            "loguru",
            "tqdm",
        ],
        "bin": [""],
    },
    "configs": {
        "api_id": {"default": None, "help": "telegram API_ID value, go to https://my.telegram.org/apps"},
        "api_hash": {"default": None, "help": "telegram API_HASH value, go to https://my.telegram.org/apps"},
        "bot_token": {
            "default": None,
            "help": "optional, but allows access to more content such as large videos, talk to @botfather",
        },
        "session_file": {
            "default": "secrets/anon",
            "help": "Path of the file to save the telegram login session for future usage, '.session' will be appended to the provided path.",
        },
        "join_channels": {
            "default": True,
            "type": "bool",
            "help": "disables the initial setup with channel_invites config, useful if you have a lot and get stuck",
        },
        "channel_invites": {
            "default": {},
            "help": "(JSON string) private channel invite links (format: t.me/joinchat/HASH OR t.me/+HASH) and (optional but important to avoid hanging for minutes on startup) channel id (format: CHANNEL_ID taken from a post url like https://t.me/c/CHANNEL_ID/1), the telegram account will join any new channels on setup",
            "type": "json_loader",
        },
    },
    "description": """
The `TelethonExtractor` uses the Telethon library to archive posts and media from Telegram channels and groups. 
It supports private and public channels, downloading grouped posts with media, and can join channels using invite links 
if provided in the configuration. 

### Features
- Fetches posts and metadata from Telegram channels and groups, including private channels.
- Downloads media attachments (e.g., images, videos, audio) from individual posts or grouped posts.
- Handles channel invites to join channels dynamically during setup.
- Utilizes Telethon's capabilities for reliable Telegram interactions.
- Outputs structured metadata and media using `Metadata` and `Media` objects.

### Setup
To use the `TelethonExtractor`, you must configure the following:
- **API ID and API Hash**: Obtain these from [my.telegram.org](https://my.telegram.org/apps).
- **Session File**: Optional, but records login sessions for future use (default: `secrets/anon.session`).
- **Bot Token**: Optional, allows access to additional content (e.g., large videos) but limits private channel archiving.
- **Channel Invites**: Optional, specify a JSON string of invite links to join channels during setup.

### First Time Login
The first time you run, you will be prompted to do a authentication with the phone number associated, alternatively you can put your `anon.session` in the root.


""",
}
