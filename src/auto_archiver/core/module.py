"""
Defines the Step abstract base class, which acts as a blueprint for steps in the archiving pipeline
by handling user configuration, validating the steps properties, and implementing dynamic instantiation.

"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List
import shutil
import ast
import copy
import sys
from importlib.util import find_spec
import os
from os.path import join, dirname
from loguru import logger
import auto_archiver
from .base_module import BaseModule

_LAZY_LOADED_MODULES = {}

MANIFEST_FILE = "__manifest__.py"


def setup_paths(paths: list[str]) -> None:
    """
    Sets up the paths for the modules to be loaded from
    
    This is necessary for the modules to be imported correctly
    
    """
    for path in paths:
        # check path exists, if it doesn't, log a warning
        if not os.path.exists(path):
            logger.warning(f"Path '{path}' does not exist. Skipping...")
            continue

        # see odoo/module/module.py -> initialize_sys_path
        if path not in auto_archiver.modules.__path__:
                auto_archiver.modules.__path__.append(path)

    # sort based on the length of the path, so that the longest path is last in the list
    auto_archiver.modules.__path__ = sorted(auto_archiver.modules.__path__, key=len, reverse=True)


def get_module(module_name: str, config: dict) -> BaseModule:
    """
    Gets and sets up a module using the provided config
    
    This will actually load and instantiate the module, and load all its dependencies (i.e. not lazy)
    
    """
    return get_module_lazy(module_name).load(config)

def get_module_lazy(module_name: str, suppress_warnings: bool = False) -> LazyBaseModule:
    """
    Lazily loads a module, returning a LazyBaseModule
    
    This has all the information about the module, but does not load the module itself or its dependencies
    
    To load an actual module, call .setup() on a laz module
    
    """
    if module_name in _LAZY_LOADED_MODULES:
        return _LAZY_LOADED_MODULES[module_name]

    module = available_modules(limit_to_modules=[module_name], suppress_warnings=suppress_warnings)[0]
    return module

def available_modules(with_manifest: bool=False, limit_to_modules: List[str]= [], suppress_warnings: bool = False) -> List[LazyBaseModule]:
    # search through all valid 'modules' paths. Default is 'modules' in the current directory

    # see odoo/modules/module.py -> get_modules
    def is_really_module(module_path):
        if os.path.isfile(join(module_path, MANIFEST_FILE)):
            return True

    all_modules = []

    for module_folder in auto_archiver.modules.__path__:
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
            if _LAZY_LOADED_MODULES.get(possible_module):
                continue
            lazy_module = LazyBaseModule(possible_module, possible_module_path)

            _LAZY_LOADED_MODULES[possible_module] = lazy_module

            all_modules.append(lazy_module)
    
    if not suppress_warnings:
        for module in limit_to_modules:
            if not any(module == m.name for m in all_modules):
                logger.warning(f"Module '{module}' not found. Are you sure it's installed?")

    return all_modules

@dataclass
class LazyBaseModule:

    """
    A lazy module class, which only loads the manifest and does not load the module itself.

    This is useful for getting information about a module without actually loading it.

    """
    name: str
    type: list
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
    def dependencies(self) -> dict:
        return self.manifest['dependencies']
    
    @property
    def configs(self) -> dict:
        return self.manifest['configs']
    
    @property
    def requires_setup(self) -> bool:
        return self.manifest['requires_setup']
    
    @property
    def display_name(self) -> str:
        return self.manifest['name']

    @property
    def manifest(self) -> dict:
        if self._manifest:
            return self._manifest
        # print(f"Loading manifest for module {module_path}")
        # load the manifest file
        manifest = copy.deepcopy(BaseModule._DEFAULT_MANIFEST)

        with open(join(self.path, MANIFEST_FILE)) as f:
            try:
                manifest.update(ast.literal_eval(f.read()))
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as e:
                logger.error(f"Error loading manifest from file {self.path}/{MANIFEST_FILE}: {e}")
            
        self._manifest = manifest
        self.type = manifest['type']
        self._entry_point = manifest['entry_point']
        self.description = manifest['description']
        self.version = manifest['version']

        return manifest

    def load(self, config) -> BaseModule:

        if self._instance:
            return self._instance

        # check external dependencies are installed
        def check_deps(deps, check):
            for dep in deps:
                if not len(dep):
                    # clear out any empty strings that a user may have erroneously added
                    continue
                if not check(dep):
                    logger.error(f"Module '{self.name}' requires external dependency '{dep}' which is not available/setup. Have you installed the required dependencies for the '{self.name}' module? See the README for more information.")
                    exit(1)

        def check_python_dep(dep):
            # first check if it's a module:
            try:
                m = get_module_lazy(dep, suppress_warnings=True)
                try:
                # we must now load this module and set it up with the config
                    m.load(config)
                    return True
                except:
                    logger.error(f"Unable to setup module '{dep}' for use in module '{self.name}'")
                    return False
            except IndexError:
                # not a module, continue
                pass

            return find_spec(dep)

        check_deps(self.dependencies.get('python', []), check_python_dep)
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
        instance: BaseModule = getattr(sys.modules[sub_qualname], class_name)()
        if not getattr(instance, 'name', None):
            instance.name = self.name

        if not getattr(instance, 'display_name', None):
            instance.display_name = self.display_name

        self._instance = instance

        # merge the default config with the user config
        default_config = dict((k, v['default']) for k, v in self.configs.items() if v.get('default'))
        config[self.name] = default_config  | config.get(self.name, {})
        instance.setup(config)
        return instance

    def __repr__(self):
        return f"Module<'{self.display_name}' ({self.name})>"