{
    "name": "Antibot Extractor/Enricher",
    "type": ["extractor", "enricher"],
    "requires_setup": False,
    "dependencies": {
        "python": ["loguru", "seleniumbase"],
    },
    "configs": {
        "save_to_pdf": {
            "default": False,
            "type": "bool",
            "help": "save a PDF snapshot of the page.",
        },
        "max_download_images": {
            "default": 50,
            "help": "maximum number of images to download from the page (0 = no download, inf = no limit).",
        },
        "max_download_videos": {
            "default": 50,
            "help": "maximum number of videos to download from the page (0 = no download, inf = no limit).",
        },
        "exclude_media_extensions": {
            "default": ".svg,.ico,.gif",
            "help": "CSV of media (image/video) file extensions to exclude from download",
        },
        "proxy": {
            "default": None,
            "help": "proxy to use for the webdriver, Format: 'SERVER:PORT' or 'USER:PASS@SERVER:PORT'",
        },
    },
    "description": """
    Uses a browser controlled by SeleniumBase to capture HTML, media, and screenshots/PDFs of a web page, by bypassing anti-bot measures like Cloudflare's Turnstile.

    ### Features
	- Extracts the HTML source code of the page.
    - Takes full-page screenshots of web pages.
	- Takes full-page PDF snapshots of web pages.
	- Downloads images and videos from the page, excluding specified file extensions.

    ### Notes
    - Requires a WebDriver (e.g., ChromeDriver) installed and accessible via the system's PATH.
	- Using a proxy affects Cloudflare Turnstile captcha handling, so it is recommended to use a proxy only if necessary.
    """,
}
