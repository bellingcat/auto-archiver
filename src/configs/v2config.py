

import argparse, yaml
from dataclasses import dataclass, field
from typing import List
from archivers import Archiverv2
from feeders import Feeder
from steps.step import Step
from enrichers import Enricher
from collections import defaultdict


@dataclass
class ConfigV2:
    # TODO: should Config inherit from Step so it can have it's own configurations?
    configurable_parents = [
        Feeder,
        Enricher,
        Archiverv2,
        # Util
    ]
    feeder: Step  # TODO:= BaseFeeder
    archivers: List[Archiverv2] = field(default_factory=[])  # TODO: fix type
    enrichers: List[Enricher] = field(default_factory=[])
    formatters: List[Step] = field(default_factory=[])  # TODO: fix type
    storages: List[Step] = field(default_factory=[])  # TODO: fix type
    databases: List[Step] = field(default_factory=[])  # TODO: fix type

    def __init__(self) -> None:
        self.defaults = {}
        self.cli_ops = {}
        self.config = {}

    # TODO: make this work for nested props like gsheets_feeder.columns.url = "URL"
    def parse(self):
        # 1. parse CLI values
        parser = argparse.ArgumentParser(
            # prog = "auto-archiver",
            description="Auto Archiver is a ...!",
            epilog="Check the code at https://github.com/bellingcat/auto-archiver"
        )

        parser.add_argument('--config', action='store', dest='config', help='the filename of the YAML configuration file (defaults to \'config.yaml\')', default='config.yaml')

        for configurable in self.configurable_parents:
            child: Step
            for child in configurable.__subclasses__():
                for config, details in child.configs().items():
                    assert "." not in child.name, f"class prop name cannot contain dots('.'): {child.name}"
                    assert "." not in config, f"config property cannot contain dots('.'): {config}"
                    config_path = f"{child.name}.{config}"
                    parser.add_argument(f'--{config_path}', action='store', dest=config_path, help=f"{details['help']} (defaults to {details['default']})")
                    self.defaults[config_path] = details["default"]
                    if "cli_set" in details:
                        self.cli_ops[config_path] = details["cli_set"]

        args = parser.parse_args()

        # 2. read YAML config file
        with open(args.config, "r", encoding="utf-8") as inf:
            self.yaml_config = yaml.safe_load(inf)

        # print(f"{self.yaml_config.get('configurations', {})=}")
        # 3. CONFIGS: decide value with priority: CLI >> config.yaml >> default
        self.config = defaultdict(dict)
        for config_path, default in self.defaults.items():
            child, config = tuple(config_path.split("."))
            val = getattr(args, config_path)
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
        self.enrichers = [Enricher.init(e, self.config) for e in steps.get("enrichers", [])]
        self.archivers = [Archiverv2.init(e, self.config) for e in steps.get("archivers", [])]

        print("feeder", self.feeder)
        print("enrichers", [e for e in self.enrichers])
        print("archivers", [e for e in self.archivers])

    def validate(self):
        pass
