import ast
from dataclasses import dataclass, field
import os
import copy
from os.path import join, dirname
from typing import List
from loguru import logger
import sys
import shutil

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

def load_modules(modules):
    modules = available_modules(limit_to_modules=modules, with_manifest=True)
    for module in modules:
        _load_module(module)

def _load_module(module):
    # first make sure that the 'depends' are installed and available in sys.args
    for dependency in module.depends:
        if dependency not in sys.modules:
            logger.error(f"""
                            Module {module.name} depends on {dependency} which is not available.
                            
                            Have you set up the '{module.name}' module correctly? See the README for more information.
                            """)
            exit()
    # then check the external dependencies, these are binary dependencies that should be available on the path
    for dep_type, deps in module.external_dependencies.items():
        if dep_type == 'python':
            for dep in deps:
                if dep not in sys.modules:
                    logger.error(f"""
                                Module {module.name} requires {dep} which is not available.
                                
                                Have you installed the required dependencies for the '{module.name}' module? See the README for more information.
                                """)

        elif dep_type == 'binary':
            for dep in deps:
                if not shutil.which(dep):
                    logger.error(f"""
                                Module {module.name} requires {dep} which is not available.
                                
                                Have you installed the required dependencies for the '{module.name}' module? See the README for more information.
                                """)
    # finally, load the module
    logger.info(f"Loading module {module.display_name}")
    module = __import__(module.entry_point, fromlist=[module.entry_point])
    logger.info(f"Module {module.display_name} loaded")

def load_manifest(module_path):
    # print(f"Loading manifest for module {module_path}")
    # load the manifest file
    manifest = copy.deepcopy(_DEFAULT_MANIFEST)

    with open(join(module_path, MANIFEST_FILE)) as f:
        manifest.update(ast.literal_eval(f.read()))
    return manifest

def available_modules(with_manifest: bool=False, limit_to_modules: List[str]= [], additional_paths: List[str] = [], ) -> List[Module]:
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
    
    for module in limit_to_modules:
        if not any(module == m.name for m in all_modules):
            logger.warning(f"Module {module} not found in available modules. Are you sure it's installed?")

    return all_modules