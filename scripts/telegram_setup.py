"""
This script is used to create a new session file for the Telegram client.
To do this you must first create a Telegram application at https://my.telegram.org/apps
And store your id and hash in the environment variables TELEGRAM_API_ID and TELEGRAM_API_HASH.
Create a .env file, or add the following to your environment :
```
export TELEGRAM_API_ID=[YOUR_ID_HERE]
export TELEGRAM_API_HASH=[YOUR_HASH_HERE]
```
Then run this script to create a new session file.

You will need to provide your phone number and a 2FA code the first time you run this script.
"""

import os
from telethon.sync import TelegramClient
from auto_archiver.utils.custom_logger import logger


# Create a
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_FILE = "secrets/anon-insta"

os.makedirs("secrets", exist_ok=True)
with TelegramClient(SESSION_FILE, API_ID, API_HASH) as client:
    logger.success(f"new session file created: {SESSION_FILE}.session")
