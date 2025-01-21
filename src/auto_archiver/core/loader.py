import ast
import os
import copy
from os.path import join, dirname
from typing import List

MANIFEST_FILE = "__manifest__.py"
_DEFAULT_MANIFEST = {
    'author': 'Bellingcat',
    'requires_setup': True,
    'depends': [],
    'description': '',
    'external_dependencies': {},
    'entry_point': '',
    'version': '1.0',
    'config': {}
}

def load_manifest(module):
    # load the manifest file
    manifest = copy.deepcopy(_DEFAULT_MANIFEST)

    with open(join(module, MANIFEST_FILE)) as f:
        manifest.update(ast.literal_eval(f.read()))
    return manifest

def available_modules(additional_paths: List[str] = [], with_manifest: bool=False) -> List[dict]:
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
            all_modules.append((possible_module, possible_module_path, manifest))

    return all_modules