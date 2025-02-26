# iterate through all the modules in auto_archiver.modules and turn the __manifest__.py file into a markdown table
from pathlib import Path
from auto_archiver.core.module import ModuleFactory
from auto_archiver.core.base_module import BaseModule
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
import io

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

EXAMPLE_YAML = """
# steps configuration
steps:
...
{steps_str}
...

# module configuration
...

{config_string}

"""

def generate_module_docs():
    yaml = YAML()
    SAVE_FOLDER.mkdir(exist_ok=True)
    modules_by_type = {}

    header_row = "| " + " | ".join(TABLE_HEADER) + "|\n" + "| --- " * len(TABLE_HEADER) + "|\n"
    global_table = "\n## Configuration Options\n" + header_row

    global_yaml = yaml.load("""\n# Module configuration\nplaceholder: {}""")

    for module in sorted(ModuleFactory().available_modules(), key=lambda x: (x.requires_setup, x.name)):
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
        steps_str = "\n".join(f"  {t}s:\n  - {module.name}" for t in manifest['type'])

        if not manifest['configs']:
            config_string = f"# No configuration options for {module.name}.*\n"
        else:

            config_table = header_row
            config_yaml = {}

            global_yaml[module.name] = CommentedMap()
            global_yaml.yaml_set_comment_before_after_key(module.name, f"\n\n{module.display_name} configuration options")


            for key, value in manifest['configs'].items():
                type = value.get('type', 'string')
                if type == 'json_loader':
                    value['type'] = 'json'
                elif type == 'str':
                    type = "string"
                
                default = value.get('default', '')
                config_yaml[key] = default

                global_yaml[module.name][key] = default

                if value.get('help', ''):
                    global_yaml[module.name].yaml_add_eol_comment(value.get('help', ''), key)

                help = "**Required**. " if value.get('required', False) else "Optional. "
                help += value.get('help', '')
                config_table += f"| `{module.name}.{key}` | {help} | {value.get('default', '')} | {type} |\n"
                global_table += f"| `{module.name}.{key}` | {help} | {default} | {type} |\n"
            readme_str += "\n## Configuration Options\n"
            readme_str += "\n### YAML\n"

            config_string = io.BytesIO()
            yaml.dump({module.name: config_yaml}, config_string)
            config_string = config_string.getvalue().decode('utf-8')
        yaml_string = EXAMPLE_YAML.format(steps_str=steps_str, config_string=config_string)
        readme_str += f"```{{code}} yaml\n{yaml_string}\n```\n"

        if manifest['configs']:
            readme_str += "\n### Command Line:\n"
            readme_str += config_table

        # add a link to the autodoc refs
        readme_str += f"\n[API Reference](../../../autoapi/{module.name}/index)\n"
        # create the module.type folder, use the first type just for where to store the file
        for type in manifest['type']:
            type_folder = SAVE_FOLDER / type
            type_folder.mkdir(exist_ok=True)
            with open(type_folder / f"{module.name}.md", "w") as f:
                print("writing", SAVE_FOLDER)
                f.write(readme_str)
        generate_index(modules_by_type)

    del global_yaml['placeholder']
    global_string = io.BytesIO()
    global_yaml = yaml.dump(global_yaml, global_string)
    global_string = global_string.getvalue().decode('utf-8')
    global_yaml = f"```yaml\n{global_string}\n```"
    with open(SAVE_FOLDER / "configs_cheatsheet.md", "w") as f:
        f.write("### Configuration File\n" + global_yaml + "\n### Command Line\n" + global_table)


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


if __name__ == "__main__":
    generate_module_docs()