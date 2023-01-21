

import argparse, yaml
from dataclasses import dataclass, field
from typing import List
from collections import defaultdict

from ..archivers import Archiver
from ..feeders import Feeder
from ..databases import Database
from ..formatters import Formatter
from ..storages import Storage
from . import Step
from ..enrichers import Enricher


@dataclass
class Config:
    # TODO: should Config inherit from Step so it can have it's own configurations?
    # these are only detected if they are put to the respective __init__.py
    configurable_parents = [
        Feeder,
        Enricher,
        Archiver,
        Database,
        Storage,
        Formatter
        # Util
    ]
    feeder: Step  # TODO:= BaseFeeder
    formatter: Formatter
    archivers: List[Archiver] = field(default_factory=[])  # TODO: fix type
    enrichers: List[Enricher] = field(default_factory=[])
    storages: List[Step] = field(default_factory=[])  # TODO: fix type
    databases: List[Database] = field(default_factory=[])

    def __init__(self) -> None:
        self.defaults = {}
        self.cli_ops = {}
        self.config = {}
    # TODO: make this work for nested props like gsheet_feeder.columns.url = "URL"

    def parse(self, use_cli=True, yaml_config_filename: str = None):
        """
        if yaml_config_filename is provided, the --config argument is ignored, 
        useful for library usage when the config values are preloaded
        """
        # 1. parse CLI values
        if use_cli:
            parser = argparse.ArgumentParser(
                # prog = "auto-archiver",
                description="Auto Archiver is a ...!",  # TODO: update
                epilog="Check the code at https://github.com/bellingcat/auto-archiver"
            )

            parser.add_argument('--config', action='store', dest='config', help='the filename of the YAML configuration file (defaults to \'config.yaml\')', default='config.yaml')

        for configurable in self.configurable_parents:
            child: Step
            for child in configurable.__subclasses__():
                assert child.configs() is not None and type(child.configs()) == dict, f"class '{child.name}' should have a configs method returning a dict."
                for config, details in child.configs().items():
                    assert "." not in child.name, f"class prop name cannot contain dots('.'): {child.name}"
                    assert "." not in config, f"config property cannot contain dots('.'): {config}"
                    config_path = f"{child.name}.{config}"
                    
                    if use_cli:
                        try:
                            parser.add_argument(f'--{config_path}', action='store', dest=config_path, help=f"{details['help']} (defaults to {details['default']})", choices=details.get("choices", None))
                        except argparse.ArgumentError:
                            # captures cases when a Step is used in 2 flows, eg: wayback enricher vs wayback archiver
                            pass

                    self.defaults[config_path] = details["default"]
                    if "cli_set" in details:
                        self.cli_ops[config_path] = details["cli_set"]

        if use_cli:
            args = parser.parse_args()
            yaml_config_filename = yaml_config_filename or getattr(args, "config")
        else: args = {}

        # 2. read YAML config file (or use provided value)
        self.yaml_config = self.read_yaml(yaml_config_filename)

        # print(f"{self.yaml_config.get('configurations', {})=}")
        # 3. CONFIGS: decide value with priority: CLI >> config.yaml >> default
        self.config = defaultdict(dict)
        for config_path, default in self.defaults.items():
            child, config = tuple(config_path.split("."))
            val = getattr(args, config_path, None)
            if val is not None and config_path in self.cli_ops:
                val = self.cli_ops[config_path](val, default)
            if val is None:
                val = self.yaml_config.get("configurations", {}).get(child, {}).get(config, default)
            # print(child, config, val)
            self.config[child][config] = val
        self.config = dict(self.config)

        # 4. STEPS: read steps and validate they exist
        steps = self.yaml_config.get("steps", {})
        assert "archivers" in steps, "your configuration steps are missing the archivers property"
        assert "storages" in steps, "your configuration steps are missing the storages property"

        # print("config.py", self.config)

        self.feeder = Feeder.init(steps.get("feeder", "cli_feeder"), self.config)
        self.formatter = Formatter.init(steps.get("formatter", "html_formatter"), self.config)
        self.enrichers = [Enricher.init(e, self.config) for e in steps.get("enrichers", [])]
        self.archivers = [Archiver.init(e, self.config) for e in (steps.get("archivers") or [])]
        self.databases = [Database.init(e, self.config) for e in steps.get("databases", [])]
        self.storages = [Storage.init(e, self.config) for e in steps.get("storages", [])]

        print("feeder", self.feeder)
        print("enrichers", [e for e in self.enrichers])
        print("archivers", [e for e in self.archivers])
        print("databases", [e for e in self.databases])
        print("storages", [e for e in self.storages])
        print("formatter", self.formatter)

    def read_yaml(self, yaml_filename: str) -> dict:
        with open(yaml_filename, "r", encoding="utf-8") as inf:
            return yaml.safe_load(inf)
