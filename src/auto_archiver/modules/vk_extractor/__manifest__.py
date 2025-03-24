{
    "name": "VKontakte Extractor",
    "type": ["extractor"],
    "requires_setup": True,
    "depends": ["core", "utils"],
    "dependencies": {
        "python": ["loguru", "vk_url_scraper"],
    },
    "configs": {
        "username": {"required": True, "help": "valid VKontakte username"},
        "password": {"required": True, "help": "valid VKontakte password"},
        "session_file": {
            "default": "secrets/vk_config.v2.json",
            "help": "valid VKontakte password",
        },
    },
    "description": """
The `VkExtractor` fetches posts, text, and images from VK (VKontakte) social media pages. 
This archiver is specialized for `/wall` posts and uses the `VkScraper` library to extract 
and download content. Note that VK videos are handled separately by the `YTDownloader`.

### Features
- Extracts text, timestamps, and metadata from VK `/wall` posts.
- Downloads associated images and attaches them to the resulting `Metadata` object.
- Processes multiple segments of VK URLs that contain mixed content (e.g., wall, photo).
- Outputs structured metadata and media using `Metadata` and `Media` objects.

### Setup
To use the `VkArchiver`, you must provide valid VKontakte login credentials and session information:
- **Username**: A valid VKontakte account username.
- **Password**: The corresponding password for the VKontakte account.
- **Session File**: Optional. Path to a session configuration file (`.json`) for persistent VK login.

Credentials can be set in the configuration file or directly via environment variables. Ensure you 
have access to the VKontakte API by creating an account at [VKontakte](https://vk.com/).
""",
}
