import os
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
}

def load_manifest(self, module):
    # load the manifest file
    with open(join(module, MANIFEST_FILE)) as f:
        manifest = f.read()
    return manifest

def available_modules(self, additional_paths: List[str] = []) -> List[dict]:
    # search through all valid 'modules' paths. Default is 'modules' in the current directory

    # see odoo/modules/module.py -> get_modules
    def is_really_module(name):
        if os.path.isfile(join(name, MANIFEST_FILE)):
            return True

    default_path = [join(dirname(dirname((__file__))), "modules")]
    all_modules = []

    for module_folder in default_path + additional_paths:
        # walk through each module in module_folder and check if it has a valid manifest
        for folder in os.listdir(module_folder):
            possible_module = join(module_folder, folder)
            if not is_really_module(possible_module):
                continue
            # parse manifest and add to list of available modules
            all_modules.append(possible_module)

    return all_modules