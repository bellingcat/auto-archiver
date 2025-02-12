{
    "name": "Telegram Extractor",
    "type": ["extractor"],
    "requires_setup": False,
    "dependencies": {
        "python": [
            "requests",
            "bs4",
            "loguru",
        ],
    },
    "description": """ 
        The `TelegramExtractor` retrieves publicly available media content from Telegram message links without requiring login credentials. 
        It processes URLs to fetch images and videos embedded in Telegram messages, ensuring a structured output using `Metadata` 
        and `Media` objects. Recommended for scenarios where login-based archiving is not viable, although `telethon_archiver` 
        is advised for more comprehensive functionality, and higher quality media extraction.
        
        ### Features
- Extracts images and videos from public Telegram message links (`t.me`).
- Processes HTML content of messages to retrieve embedded media.
- Sets structured metadata, including timestamps, content, and media details.
- Does not require user authentication for Telegram.

    """,
}
