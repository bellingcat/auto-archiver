import ast
from dataclasses import dataclass, field
import os
import copy
from os.path import join, dirname
from typing import List


MODULE_TYPES = [
    'feeder',
    'enricher',
    'archiver',
    'database',
    'storage',
    'formatter'
]

MANIFEST_FILE = "__manifest__.py"
_DEFAULT_MANIFEST = {
    'name': '',
    'author': 'Bellingcat',
    'requires_setup': True,
    'depends': [],
    'description': '',
    'external_dependencies': {},
    'entry_point': '',
    'version': '1.0',
    'configs': {}
}

@dataclass
class Module:
    name: str
    display_name: str
    type: list
    entry_point: str
    depends: list
    external_dependencies: dict
    requires_setup: bool
    configs: dict
    description: str
    path: str
    manifest: dict

    def __init__(self, module_name, path, manifest):
        self.name = module_name
        self.path = path
        self.manifest = manifest
        if manifest:
            self.display_name = manifest['name']
            self.type = manifest['type']
            self.entry_point = manifest['entry_point']
            self.depends = manifest['depends']
            self.external_dependencies = manifest['external_dependencies']
            self.requires_setup = manifest['requires_setup']
            self.configs = manifest['configs']
            self.description = manifest['description']

    def __repr__(self):
        return f"Module<'{self.display_name}' ({self.name})>"



def load_manifest(module_path):
    # print(f"Loading manifest for module {module_path}")
    # load the manifest file
    manifest = copy.deepcopy(_DEFAULT_MANIFEST)

    with open(join(module_path, MANIFEST_FILE)) as f:
        manifest.update(ast.literal_eval(f.read()))
    return manifest

def available_modules(additional_paths: List[str] = [], with_manifest: bool=False) -> List[Module]:
    # search through all valid 'modules' paths. Default is 'modules' in the current directory
    
    # see odoo/modules/module.py -> get_modules
    def is_really_module(name):
        if os.path.isfile(join(name, MANIFEST_FILE)):
            return True

    default_path = [join(dirname(dirname((__file__))), "modules")]
    all_modules = []

    for module_folder in default_path + additional_paths:
        # walk through each module in module_folder and check if it has a valid manifest
        for possible_module in os.listdir(module_folder):
            possible_module_path = join(module_folder, possible_module)
            if not is_really_module(possible_module_path):
                continue
            # parse manifest and add to list of available modules
            if with_manifest:
                manifest = load_manifest(possible_module_path)
            else:
                manifest = {}
            all_modules.append(Module(possible_module, possible_module_path, manifest))

    return all_modules