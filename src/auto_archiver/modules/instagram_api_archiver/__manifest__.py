{
    "name": "Instagram API Archiver",
    "type": ["extractor"],
    "entry_point": "instagram_api_archiver:InstagramApiArchiver",
    "depends": ["core"],
    "external_dependencies":
        {"python": ["requests",
                    "loguru",
                    "retrying",
                    "tqdm",],
         },
    "no_setup_required": False,
    "configs": {
        "access_token": {"default": None, "help": "a valid instagrapi-api token"},
        "api_endpoint": {"default": None, "help": "API endpoint to use"},
        "full_profile": {
            "default": False,
            "help": "if true, will download all posts, tagged posts, stories, and highlights for a profile, if false, will only download the profile pic and information.",
        },
        "full_profile_max_posts": {
            "default": 0,
            "help": "Use to limit the number of posts to download when full_profile is true. 0 means no limit. limit is applied softly since posts are fetched in batch, once to: posts, tagged posts, and highlights",
        },
        "minimize_json_output": {
            "default": True,
            "help": "if true, will remove empty values from the json output",
        },
    },
    "description": "",
}
