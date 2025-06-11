{
    "name": "Antibot Extractor/Enricher",
    "type": ["extractor", "enricher"],
    "requires_setup": False,
    "dependencies": {"python": ["loguru", "seleniumbase", "yt_dlp"], "bin": ["ffmpeg"]},
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
        "user_data_dir": {
            "default": "secrets/antibot_user_data",
            "help": "Path to the user data directory for the webdriver. This is used to persist browser state, such as cookies and local storage. If you use the docker deployment, this path will be appended with `_docker` that is because the folder cannot be shared between the host and the container due to user permissions.",
        },
        "detect_auth_wall": {
            "default": True,
            "type": "bool",
            "help": "detect if the page is behind an authentication wall (e.g. login required) and skip it. disable if you want to archive pages where logins are required.",
        },
        "proxy": {
            "default": None,
            "help": "proxy to use for the webdriver, Format: 'SERVER:PORT' or 'USER:PASS@SERVER:PORT'",
        },
    },
    "autodoc_dropins": True,
    "description": """
    Uses a browser controlled by SeleniumBase to capture HTML, media, and screenshots/PDFs of a web page, by bypassing anti-bot measures like Cloudflare's Turnstile or Google Recaptcha.
	
	> ⚠️ Still in trial development, please report any issues or suggestions via [GitHub Issues](https://github.com/bellingcat/auto-archiver/issues).
	
    ### Features
	- Extracts the HTML source code of the page.
    - Takes full-page screenshots of web pages.
	- Takes full-page PDF snapshots of web pages.
	- Downloads images and videos from the page, excluding specified file extensions.

    ### Notes
	- Using a proxy affects Cloudflare Turnstile captcha handling, so it is recommended to use a proxy only if necessary.

	### Dropins
	This module uses sub-modules called Dropins for specific sites that allow it to handle anti-bot measures and custom Login flows. You don't need to include the dropins in your configuration, but you do need to add authentication credentials if you want to overcome login walls on those sites, see detailed instructions for each Dropin below.

    """,
}
