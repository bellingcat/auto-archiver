"""
Defines the Step abstract base class, which acts as a blueprint for steps in the archiving pipeline
by handling user configuration, validating the steps properties, and implementing dynamic instantiation.

"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List
from abc import ABC
import shutil
import ast
import copy
import sys
from importlib.util import find_spec
import os
from os.path import join, dirname
from loguru import logger

_LAZY_LOADED_MODULES = {}

MODULE_TYPES = [
    'feeder',
    'extractor',
    'enricher',
    'database',
    'storage',
    'formatter'
]

MANIFEST_FILE = "__manifest__.py"
_DEFAULT_MANIFEST = {
    'name': '',
    'author': 'Bellingcat',
    'type': [],
    'requires_setup': True,
    'description': '',
    'dependencies': {},
    'entry_point': '',
    'version': '1.0',
    'configs': {}
}

class BaseModule(ABC):

    config: dict
    name: str

    def setup(self, config: dict):
        self.config = config
        for key, val in config.get(self.name, {}).items():
            setattr(self, key, val)

def get_module(module_name: str, additional_paths: List[str] = []):
    if module_name in _LAZY_LOADED_MODULES:
        return _LAZY_LOADED_MODULES[module_name]

    module = available_modules(additional_paths=additional_paths, limit_to_modules=[module_name])[0]
    _LAZY_LOADED_MODULES[module_name] = module
    return module

def available_modules(with_manifest: bool=False, limit_to_modules: List[str]= [], additional_paths: List[str] = [], suppress_warnings: bool = False) -> List[LazyBaseModule]:
    # search through all valid 'modules' paths. Default is 'modules' in the current directory

    # see odoo/modules/module.py -> get_modules
    def is_really_module(module_path):
        if os.path.isfile(join(module_path, MANIFEST_FILE)):
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
                
            all_modules.append(LazyBaseModule(possible_module, possible_module_path))
    
    if not suppress_warnings:
        for module in limit_to_modules:
            if not any(module == m.name for m in all_modules):
                logger.warning(f"Module '{module}' not found. Are you sure it's installed?")

    return all_modules

@dataclass
class LazyBaseModule:
    name: str
    display_name: str
    type: list
    requires_setup: bool
    description: str
    path: str

    _manifest: dict = None
    _instance: BaseModule = None
    _entry_point: str = None

    def __init__(self, module_name, path):
        self.name = module_name
        self.path = path
    
    @property
    def entry_point(self):
        if not self._entry_point and not self.manifest['entry_point']:
            # try to create the entry point from the module name
            self._entry_point = f"{self.name}::{self.name.replace('_', ' ').title().replace(' ', '')}"
        return self._entry_point

    @property
    def dependencies(self):
        return self.manifest['dependencies']
    
    @property
    def configs(self):
        return self.manifest['configs']

    @property
    def manifest(self):
        if self._manifest:
            return self._manifest
        # print(f"Loading manifest for module {module_path}")
        # load the manifest file
        manifest = copy.deepcopy(_DEFAULT_MANIFEST)

        with open(join(self.path, MANIFEST_FILE)) as f:
            try:
                manifest.update(ast.literal_eval(f.read()))
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as e:
                logger.error(f"Error loading manifest from file {self.path}/{MANIFEST_FILE}: {e}")
            
        self._manifest = manifest
        self.display_name = manifest['name']
        self.type = manifest['type']
        self._entry_point = manifest['entry_point']
        self.requires_setup = manifest['requires_setup']
        self.description = manifest['description']

        return manifest

    def load(self):
            if self._instance:
                return self._instance

            # check external dependencies are installed
            def check_deps(deps, check):
                for dep in deps:
                    if not check(dep):
                        logger.error(f"Module '{self.name}' requires external dependency '{dep}' which is not available. Have you installed the required dependencies for the '{self.name}' module? See the README for more information.")
                        exit(1)
            
            check_deps(self.dependencies.get('python', []), lambda dep: find_spec(dep))
            check_deps(self.dependencies.get('bin', []), lambda dep: shutil.which(dep))
            

            logger.debug(f"Loading module '{self.display_name}'...")

            for qualname in [self.name, f'auto_archiver.modules.{self.name}']:
                try:
                    # first import the whole module, to make sure it's working properly
                    __import__(qualname)
                    break
                except ImportError:
                    pass

            # then import the file for the entry point
            file_name, class_name = self.entry_point.split('::')
            sub_qualname = f'{qualname}.{file_name}'

            __import__(f'{qualname}.{file_name}', fromlist=[self.entry_point])
            
            # finally, get the class instance
            instance = getattr(sys.modules[sub_qualname], class_name)()
            if not getattr(instance, 'name', None):
                instance.name = self.name
            
            if not getattr(instance, 'display_name', None):
                instance.display_name = self.display_name

            self._instance = instance
            return instance

    def __repr__(self):
        return f"Module<'{self.display_name}' ({self.name})>"