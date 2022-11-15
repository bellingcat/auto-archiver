

import argparse, yaml
from dataclasses import dataclass, field
from typing import List
from step import Step
from utils import Util
from enrichers import Enricher
from collections import defaultdict


@dataclass
class ConfigV2:
    # TODO: should Config inherit from Step so it can have it's own configurations?
    configurable_parents = [
        Enricher,
        Util
    ]
    feeder : Step #TODO:= BaseFeeder
    archivers: List[Step] = field(default_factory=[]) #TODO: fix type
    enrichers: List[Enricher] = field(default_factory=[])
    formatters: List[Step] = field(default_factory=[]) #TODO: fix type
    storages: List[Step] = field(default_factory=[]) #TODO: fix type
    databases: List[Step] = field(default_factory=[]) #TODO: fix type

    def __init__(self) -> None:
        self.defaults = {}
        self.config = {}

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
                    parser.add_argument(f'--{config_path}', action='store', dest=config_path, help=details['help'])
                    self.defaults[config_path] = details["default"]

        args = parser.parse_args()

        # 2. read YAML config file
        with open(args.config, "r", encoding="utf-8") as inf:
            self.yaml_config = yaml.safe_load(inf)

        # 3. CONFIGS: decide value with priority: CLI >> config.yaml >> default
        self.config = defaultdict(dict)
        for config_path, default in self.defaults.items():
            child, config = tuple(config_path.split("."))
            val = getattr(args, config_path)
            if val is None:
                val = self.yaml_config.get("configurations", {}).get(child, {}).get(config, default)
            self.config[child][config] = val
        self.config = dict(self.config)

        # 4. STEPS: read steps and validate they exist
        steps = self.yaml_config.get("steps", {})
        assert "archivers" in steps, "your configuration steps are missing the archivers property"
        assert "storages" in steps, "your configuration steps are missing the storages property"
        
        print(self.config)
        
        # self.feeder = Feeder.init
        self.enrichers = [Enricher.init(steps.get("enrichers", [])[0], self.config)]
        
        
        print(self.enrichers)

    def validate(self):
        pass
