# iterate through all the modules in auto_archiver.modules and turn the __manifest__.py file into a markdown table
from pathlib import Path
from auto_archiver.core.module import available_modules
from auto_archiver.core.base_module import BaseModule

MODULES_FOLDER = Path(__file__).parent.parent.parent.parent / "src" / "auto_archiver" / "modules"
SAVE_FOLDER = Path(__file__).parent.parent / "source" / "modules" / "autogen"

type_color = {
    'feeder': "<span style='color: #FFA500'>[feeder](/core_modules.md#feeder-modules)</a></span>",
    'extractor': "<span style='color: #00FF00'>[extractor](/core_modules.md#extractor-modules)</a></span>",
    'enricher': "<span style='color: #0000FF'>[enricher](/core_modules.md#enricher-modules)</a></span>",
    'database': "<span style='color: #FF00FF'>[database](/core_modules.md#database-modules)</a></span>",
    'storage': "<span style='color: #FFFF00'>[storage](/core_modules.md#storage-modules)</a></span>",
    'formatter': "<span style='color: #00FFFF'>[formatter](/core_modules.md#formatter-modules)</a></span>",
}

TABLE_HEADER = ("Option", "Description", "Default", "Type")

def generate_module_docs():
    SAVE_FOLDER.mkdir(exist_ok=True)
    modules_by_type = {}

    header_row = "| " + " | ".join(TABLE_HEADER) + "|\n" + "| --- " * len(TABLE_HEADER) + "|\n"
    configs_cheatsheet = "\n## Configuration Options\n"
    configs_cheatsheet += header_row

    for module in sorted(available_modules(with_manifest=True), key=lambda x: (x.requires_setup, x.name)):
        # generate the markdown file from the __manifest__.py file.

        manifest = module.manifest
        for type in manifest['type']:
            modules_by_type.setdefault(type, []).append(module)

        description = "\n".join(l.lstrip() for l in manifest['description'].split("\n"))
        types = ", ".join(type_color[t] for t in manifest['type'])
        readme_str = f"""
# {manifest['name']}
```{{admonition}} Module type

{types}
```
{description}
"""
        if manifest['configs']:
            readme_str += "\n## Configuration Options\n"
            readme_str += header_row
            for key, value in manifest['configs'].items():
                type = value.get('type', 'string')
                if type == 'auto_archiver.utils.json_loader':
                    value['type'] = 'json'
                elif type == 'str':
                    type = "string"

                help = "**Required**. " if value.get('required', False) else "Optional. "
                help += value.get('help', '')
                readme_str += f"| `{module.name}.{key}` | {help} | {value.get('default', '')} | {type} |\n"
                configs_cheatsheet += f"| `{module.name}.{key}` | {help} | {value.get('default', '')} | {type} |\n"
        

        # add a link to the autodoc refs
        readme_str += f"\n[API Reference](../../../autoapi/{module.name}/index)\n"
        # create the module.type folder, use the first type just for where to store the file
        type_folder = SAVE_FOLDER / module.type[0]
        type_folder.mkdir(exist_ok=True)
        with open(type_folder / f"{module.name}.md", "w") as f:
            print("writing", SAVE_FOLDER)
            f.write(readme_str)
        generate_index(modules_by_type)

    with open(SAVE_FOLDER / "configs_cheatsheet.md", "w") as f:
        f.write(configs_cheatsheet)


def generate_index(modules_by_type):
    readme_str = ""
    for type in BaseModule.MODULE_TYPES:
        modules = modules_by_type.get(type, [])
        module_str = f"## {type.capitalize()} Modules\n"
        for module in modules:
            module_str += f"\n[{module.manifest['name']}](/modules/autogen/{module.type[0]}/{module.name}.md)\n"
        with open(SAVE_FOLDER / f"{type}.md", "w") as f:
            print("writing", SAVE_FOLDER / f"{type}.md")
            f.write(module_str)
        readme_str += module_str

    with open(SAVE_FOLDER / "module_list.md", "w") as f:
        print("writing", SAVE_FOLDER / "module_list.md")
        f.write(readme_str)
