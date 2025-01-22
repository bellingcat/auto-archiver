import ast
from typing import Type
from importlib.util import find_spec
from dataclasses import dataclass
import os
import copy
from os.path import join, dirname
from typing import List
from loguru import logger
import sys
import shutil

_LOADED_MODULES = {}

MODULE_TYPES = [
    'feeder',
    'enricher',
    'extractor',
    'database',
    'storage',
    'formatter'
]

MANIFEST_FILE = "__manifest__.py"
_DEFAULT_MANIFEST = {
    'name': '',
    'author': 'Bellingcat',
    'requires_setup': True,
    'description': '',
    'dependencies': {},
    'entry_point': '',
    'version': '1.0',
    'configs': {}
}

@dataclass
class Module:
    name: str
    display_name: str
    type: list
    dependencies: dict
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
            self._entry_point = manifest['entry_point']
            self.dependencies = manifest['dependencies']
            self.requires_setup = manifest['requires_setup']
            self.configs = manifest['configs']
            self.description = manifest['description']
    
    @property
    def entry_point(self):
        if not self._entry_point:
            # try to create the entry point from the module name
            self._entry_point = f"{self.name}::{self.name.replace('_', ' ').title().replace(' ', '')}"
        return self._entry_point

    def __repr__(self):
        return f"Module<'{self.display_name}' ({self.name})>"

def load_module(module: str) -> object: # TODO: change return type to Step

    if module in _LOADED_MODULES:
        return _LOADED_MODULES[module]

    # load a module by name
    module = get_module(module)
    if not module:
        return None
    # check external dependencies are installed
    def check_deps(deps, check):
        for dep in deps:
            if not check(dep):
                logger.error(f"Module '{module.name}' requires external dependency '{dep}' which is not available. Have you installed the required dependencies for the '{module.name}' module? See the README for more information.")
                exit(1)
    
    check_deps(module.dependencies.get('python', []), lambda dep: find_spec(dep))
    check_deps(module.dependencies.get('bin', []), lambda dep: shutil.which(dep))

    qualname = f'auto_archiver.modules.{module.name}'

    logger.info(f"Loading module '{module.display_name}'...")
    loaded_module = __import__(qualname)
    _LOADED_MODULES[module.name] = getattr(sys.modules[qualname], module.entry_point)()
    return _LOADED_MODULES[module.name]


    # finally, load the module

def load_manifest(module_path):
    # print(f"Loading manifest for module {module_path}")
    # load the manifest file
    manifest = copy.deepcopy(_DEFAULT_MANIFEST)

    with open(join(module_path, MANIFEST_FILE)) as f:
        manifest.update(ast.literal_eval(f.read()))
    return manifest

def get_module(module_name):
    # get a module by name
    try:
        return available_modules(limit_to_modules=[module_name], with_manifest=True, suppress_warnings=True)[0]
    except IndexError:
        return None

def available_modules(with_manifest: bool=False, limit_to_modules: List[str]= [], additional_paths: List[str] = [], suppress_warnings: bool = False) -> List[Module]:
    # search through all valid 'modules' paths. Default is 'modules' in the current directory
    
    # see odoo/modules/module.py -> get_modules
    def is_really_module(name):
        if os.path.isfile(join(name, MANIFEST_FILE)):
            return True

    default_path = [join(dirname(dirname((__file__))), "modules")]
    all_modules = []

    for module_folder in default_path + additional_paths:
        # walk through each module in module_folder and check if it has a valid manifest
        try:
            possible_modules = os.listdir(module_folder)
        except FileNotFoundError:
            logger.warning(f"Module folder {module_folder} does not exist")
            continue

        for possible_module in possible_modules:
            if limit_to_modules and possible_module not in limit_to_modules:
                continue

            possible_module_path = join(module_folder, possible_module)
            if not is_really_module(possible_module_path):
                continue
            # parse manifest and add to list of available modules
            if with_manifest:
                manifest = load_manifest(possible_module_path)
            else:
                manifest = {}
            all_modules.append(Module(possible_module, possible_module_path, manifest))
    
    if not suppress_warnings:
        for module in limit_to_modules:
            if not any(module == m.name for m in all_modules):
                logger.warning(f"Module '{module}' not found in available modules. Are you sure it's installed?")

    return all_modules