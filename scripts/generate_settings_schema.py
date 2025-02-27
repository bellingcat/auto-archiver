import json
import os

from auto_archiver.core.module import ModuleFactory
from auto_archiver.core.consts import MODULE_TYPES


class SchemaEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

# Get available modules
module_factory = ModuleFactory()
available_modules = module_factory.available_modules()

modules_by_type = {}
# Categorize modules by type
for module in available_modules:
    for type in module.manifest.get('type', []):
        modules_by_type.setdefault(type, []).append(module)

all_modules_ordered_by_type = sorted(available_modules, key=lambda x: (MODULE_TYPES.index(x.type[0]), not x.requires_setup))

output_schame = {
    'modules': dict((module.name, 
                     {
                         'name': module.name,
                         'display_name': module.display_name,
                         'manifest': module.manifest,
                         'configs': module.configs or None
                         }
                         ) for module in all_modules_ordered_by_type),
    'steps': dict((f"{module_type}s", [module.name for module in modules_by_type[module_type]]) for module_type in MODULE_TYPES),
    'configs': [m.name for m in all_modules_ordered_by_type if m.configs],
    'module_types': MODULE_TYPES,
}

current_file_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(current_file_dir, 'settings/src/schema.json')
with open(output_file, 'w') as file:
    json.dump(output_schame, file, indent=4, cls=SchemaEncoder)