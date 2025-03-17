{
    "name": "Command Line Feeder",
    "type": ["feeder"],
    "entry_point": "cli_feeder::CLIFeeder",
    "requires_setup": False,
    "configs": {
        "urls": {
            "default": None,
            "help": "URL(s) to archive, either a single URL or a list of urls, should not come from config.yaml",
        },
    },
    "description": """
The Command Line Feeder is the default enabled feeder for the Auto Archiver. It allows you to pass URLs directly to the orchestrator from the command line 
without the need to specify any additional configuration or command line arguments:

`auto-archiver --feeder cli_feeder -- "https://example.com/1/,https://example.com/2/"`

You can pass multiple URLs by separating them with a space. The URLs will be processed in the order they are provided.

`auto-archiver --feeder cli_feeder -- https://example.com/1/ https://example.com/2/`
""",
}
