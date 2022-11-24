

import argparse, yaml
from dataclasses import dataclass, field
from typing import List
from feeders.feeder import Feeder
from step import Step
from utils import Util
from enrichers import Enricher
from collections import defaultdict


@dataclass
class ConfigV2:
    # TODO: should Config inherit from Step so it can have it's own configurations?
    configurable_parents = [
        Feeder,
        Enricher,
        # Util
    ]
    feeder: Step  # TODO:= BaseFeeder
    archivers: List[Step] = field(default_factory=[])  # TODO: fix type
    enrichers: List[Enricher] = field(default_factory=[])
    formatters: List[Step] = field(default_factory=[])  # TODO: fix type
    storages: List[Step] = field(default_factory=[])  # TODO: fix type
    databases: List[Step] = field(default_factory=[])  # TODO: fix type

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
            # print(f"{configurable=}")
            for child in configurable.__subclasses__():
                # print(f"{child=} {child.configs()=}")

                for config, details in child.configs().items():
                    print(config, details)
                    assert "." not in child.name, f"class prop name cannot contain dots('.'): {child.name}"
                    assert "." not in config, f"config property cannot contain dots('.'): {config}"
                    if (is_nested := type(details["default"]) == dict):
                        for subconfig, subdefault in details["default"].items():
                            assert "." not in subconfig, f"config subproperty cannot contain dots('.'): {subconfig}"
                            config_path = f"{child.name}.{config}.{subconfig}"
                            parser.add_argument(f'--{config_path}', action='store', dest=config_path, help=details['help'] + f"({subconfig})")
                            self.defaults[config_path] = subdefault

                    config_path = f"{child.name}.{config}"
                    print(config_path)
                    self.defaults[config_path] = details["default"]
                    if not is_nested:
                        # nested cannot be directly set on the CLI
                        parser.add_argument(f'--{config_path}', action='store', dest=config_path, help=details['help'])

        args = parser.parse_args()

        # 2. read YAML config file
        with open(args.config, "r", encoding="utf-8") as inf:
            self.yaml_config = yaml.safe_load(inf)

        # print(f"{self.yaml_config.get('configurations', {})=}")
        # 3. CONFIGS: decide value with priority: CLI >> config.yaml >> default
        self.config = defaultdict(dict)
        for config_path, default in self.defaults.items():
            config_steps = config_path.split(".")
            if len(config_steps) == 2:  # not nested
                child, config = tuple(config_steps)
                val = getattr(args, config_path, None)
                if val is None:
                    val = self.yaml_config.get("configurations", {}).get(child, {}).get(config, default)
                # self.config[child][config] = val

            elif len(config_steps) == 3:  # nested
                child, config, subconfig = tuple(config_steps)
                val = getattr(args, config_path)
                if config not in self.config[child]:
                    self.config[child][config] = {}
                if val is None:
                    val = self.yaml_config.get("configurations", {}).get(child, {}).get(config, {}).get(subconfig, default)
                print(child, config, subconfig, val)
                self.config[child][config][subconfig] = val

            # child, config = tuple(config_path.split("."))
            # # print(config_path)
            # val = getattr(args, config_path)
            # # print(child, config, val)
            # if val is None:
            #     val = self.yaml_config.get("configurations", {}).get(child, {}).get(config, default)
            # self.config[child][config] = val
        self.config = dict(self.config)

        # 4. STEPS: read steps and validate they exist
        steps = self.yaml_config.get("steps", {})
        assert "archivers" in steps, "your configuration steps are missing the archivers property"
        assert "storages" in steps, "your configuration steps are missing the storages property"

        print("config.py", self.config)

        self.feeder = Feeder.init(steps.get("feeder", "cli_feeder"), self.config)
        self.enrichers = [Enricher.init(e, self.config) for e in steps.get("enrichers", [])]

        print("enrichers", [e for e in self.enrichers])

    def validate(self):
        pass
