{
    "name": "Metadata JSON Enricher",
    "type": ["enricher"],
    "requires_setup": True,
    "dependencies": {
        "python": ["loguru"],
    },
    "configs": {
        # "width": {"default": 1280, "type": "int", "help": "width of the screenshots"},
        # "height": {"default": 1024, "type": "int", "help": "height of the screenshots"},
        # "timeout": {"default": 60, "type": "int", "help": "timeout for taking the screenshot"},
        # "sleep_before_screenshot": {
        #     "default": 4,
        #     "type": "int",
        #     "help": "seconds to wait for the pages to load before taking screenshot",
        # },
        # "http_proxy": {
        #     "default": "",
        #     "help": "http proxy to use for the webdriver, eg http://proxy-user:password@proxy-ip:port",
        # },
        # "save_to_pdf": {
        #     "default": False,
        #     "type": "bool",
        #     "help": "save the page as pdf along with the screenshot. PDF saving options can be adjusted with the 'print_options' parameter",
        # },
        # "print_options": {
        #     "default": {},
        #     "help": "options to pass to the pdf printer, in JSON format. See https://www.selenium.dev/documentation/webdriver/interactions/print_page/ for more information",
        #     "type": "json_loader",
        # },
    },
    "description": """

    Writes all the metadata to a json file so can be parsed by other tools.

    """,
}
