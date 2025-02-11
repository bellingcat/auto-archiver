def get_atlos_config_options():
    return {
        "api_token": {
            "default": None,
            "help": "An Atlos API token. For more information, see https://docs.atlos.org/technical/api/",
            "type": str
        },
        "atlos_url": {
            "default": "https://platform.atlos.org",
            "help": "The URL of your Atlos instance (e.g., https://platform.atlos.org), without a trailing slash.",
            "type": str
        },
    }