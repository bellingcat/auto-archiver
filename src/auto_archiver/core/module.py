"""
Defines the Step abstract base class, which acts as a blueprint for steps in the archiving pipeline
by handling user configuration, validating the steps properties, and implementing dynamic instantiation.

"""

from __future__ import annotations
import subprocess

from dataclasses import dataclass
from typing import List, TYPE_CHECKING, Type
import shutil
import ast
import copy
import sys
from importlib.util import find_spec
import os
from os.path import join
from loguru import logger
import auto_archiver
from auto_archiver.core.consts import DEFAULT_MANIFEST, MANIFEST_FILE, SetupError

if TYPE_CHECKING:
    from .base_module import BaseModule


HAS_SETUP_PATHS = False


class ModuleFactory:
    def __init__(self):
        self._lazy_modules = {}

    def setup_paths(self, paths: list[str]) -> None:
        """
        Sets up the paths for the modules to be loaded from

        This is necessary for the modules to be imported correctly

        """
        global HAS_SETUP_PATHS

        for path in paths:
            # check path exists, if it doesn't, log a warning
            if not os.path.exists(path):
                logger.warning(f"Path '{path}' does not exist. Skipping...")
                continue

            # see odoo/module/module.py -> initialize_sys_path
            if path not in auto_archiver.modules.__path__:
                if HAS_SETUP_PATHS:
                    logger.warning(
                        f"You are attempting to re-initialise the module paths with: '{path}' for a 2nd time. \
                                       This could lead to unexpected behaviour. It is recommended to only use a single modules path. \
                                       If you wish to load modules from different paths then load a 2nd python interpreter (e.g. using multiprocessing)."
                    )
                auto_archiver.modules.__path__.append(path)

        # sort based on the length of the path, so that the longest path is last in the list
        auto_archiver.modules.__path__ = sorted(auto_archiver.modules.__path__, key=len, reverse=True)

        HAS_SETUP_PATHS = True

    def get_module(self, module_name: str, config: dict) -> Type[BaseModule]:
        """
        Gets and sets up a module using the provided config

        This will actually load and instantiate the module, and load all its dependencies (i.e. not lazy)

        """
        return self.get_module_lazy(module_name).load(config)

    def get_module_lazy(self, module_name: str, suppress_warnings: bool = False) -> LazyBaseModule:
        """
        Lazily loads a module, returning a LazyBaseModule

        This has all the information about the module, but does not load the module itself or its dependencies

        To load an actual module, call .setup() on a lazy module

        """
        if module_name in self._lazy_modules:
            return self._lazy_modules[module_name]

        available = self.available_modules(limit_to_modules=[module_name], suppress_warnings=suppress_warnings)
        if not available:
            message = f"Module '{module_name}' not found. Are you sure it's installed/exists?"
            if "archiver" in module_name:
                message += f" Did you mean '{module_name.replace('archiver', 'extractor')}'?"
            elif "gsheet" in module_name:
                message += " Did you mean 'gsheet_feeder_db'?"
            elif "atlos" in module_name:
                message += " Did you mean 'atlos_feeder_db_storage'?"
            raise IndexError(message)
        return available[0]

    def available_modules(
        self, limit_to_modules: List[str] = [], suppress_warnings: bool = False
    ) -> List[LazyBaseModule]:
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
                if self._lazy_modules.get(possible_module):
                    continue
                lazy_module = LazyBaseModule(possible_module, possible_module_path, factory=self)

                self._lazy_modules[possible_module] = lazy_module

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
    description: str
    path: str
    module_factory: ModuleFactory

    _manifest: dict = None
    _instance: BaseModule = None
    _entry_point: str = None

    def __init__(self, module_name, path, factory: ModuleFactory):
        self.name = module_name
        self.path = path
        self.module_factory = factory

    @property
    def type(self):
        return self.manifest["type"]

    @property
    def entry_point(self):
        if not self._entry_point and not self.manifest["entry_point"]:
            # try to create the entry point from the module name
            self._entry_point = f"{self.name}::{self.name.replace('_', ' ').title().replace(' ', '')}"
        return self._entry_point

    @property
    def dependencies(self) -> dict:
        return self.manifest["dependencies"]

    @property
    def configs(self) -> dict:
        return self.manifest["configs"]

    @property
    def requires_setup(self) -> bool:
        return self.manifest["requires_setup"]

    @property
    def display_name(self) -> str:
        return self.manifest["name"]

    @property
    def manifest(self) -> dict:
        if self._manifest:
            return self._manifest
        # print(f"Loading manifest for module {module_path}")
        # load the manifest file
        manifest = copy.deepcopy(DEFAULT_MANIFEST)

        with open(join(self.path, MANIFEST_FILE)) as f:
            try:
                manifest.update(ast.literal_eval(f.read()))
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as e:
                raise ValueError(f"Error loading manifest from file {self.path}/{MANIFEST_FILE}: {e}") from e

        self._manifest = manifest
        self._entry_point = manifest["entry_point"]
        self.description = manifest["description"]
        self.version = manifest["version"]

        return manifest

    def load(self, config) -> BaseModule:
        if self._instance:
            return self._instance

        # check external dependencies are installed
        def check_deps(deps, check):
            for dep in filter(lambda d: len(d.strip()) > 0, deps):
                if not check(dep.strip()):
                    logger.error(
                        f"Module '{self.name}' requires external dependency '{dep}' which is not available/setup. \
                                 Have you installed the required dependencies for the '{self.name}' module? See the documentation for more information."
                    )
                    raise SetupError()

        def check_python_dep(dep):
            # first check if it's a module:
            try:
                m = self.module_factory.get_module_lazy(dep, suppress_warnings=True)
                try:
                    # we must now load this module and set it up with the config
                    m.load(config)
                    return True
                except Exception:
                    logger.error(f"Unable to setup module '{dep}' for use in module '{self.name}'")
                    return False
            except IndexError:
                # not a module, continue
                pass

            return find_spec(dep)

        def check_bin_dep(dep):
            dep_exists = shutil.which(dep)

            if dep == "docker":
                if os.environ.get("RUNNING_IN_DOCKER"):
                    # this is only for the WACZ enricher, which requires docker
                    # if we're already running in docker then we don't need docker
                    return True

                # check if docker daemon is running
                return dep_exists and subprocess.run(["docker", "ps", "-q"]).returncode == 0

            return dep_exists

        check_deps(self.dependencies.get("python", []), check_python_dep)
        check_deps(self.dependencies.get("bin", []), check_bin_dep)

        logger.debug(f"Loading module '{self.display_name}'...")

        for qualname in [self.name, f"auto_archiver.modules.{self.name}"]:
            try:
                # first import the whole module, to make sure it's working properly
                __import__(qualname)
                break
            except ImportError:
                pass

        # then import the file for the entry point
        file_name, class_name = self.entry_point.split("::")
        sub_qualname = f"{qualname}.{file_name}"

        __import__(f"{qualname}.{file_name}", fromlist=[self.entry_point])
        # finally, get the class instance
        instance: BaseModule = getattr(sys.modules[sub_qualname], class_name)()

        # save the instance for future easy loading
        self._instance = instance

        # set the name, display name and module factory
        instance.name = self.name
        instance.display_name = self.display_name
        instance.module_factory = self.module_factory

        # merge the default config with the user config
        default_config = dict((k, v["default"]) for k, v in self.configs.items() if "default" in v)

        config[self.name] = default_config | config.get(self.name, {})
        instance.config_setup(config)
        instance.setup()

        return instance

    def __repr__(self):
        return f"Module<'{self.display_name}' ({self.name})>"
