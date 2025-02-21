import os
from auto_archiver.core.module import ModuleFactory
from auto_archiver.core.consts import MODULE_TYPES
import jinja2

# Get available modules
module_factory = ModuleFactory()
available_modules = module_factory.available_modules()

modules_by_type = {}
# Categorize modules by type
for module in available_modules:
    for type in module.manifest.get('type', []):
        modules_by_type.setdefault(type, []).append(module)


module_sections = ""
# Add module sections
for module_type in MODULE_TYPES:
    module_sections += f"<div class='module-section'><h3>{module_type.title()}s</h3>"
    # make this section in rows, max 8 modules per row
    for module in modules_by_type[module_type]:
        
        module_name = module.name
        module_sections += f"""
            <div style="display:inline-block; width: 12.5%;">
                <input type="checkbox" id="{module.name}" name="{module.name}" onclick="toggleModuleConfig(this, '{module.name}')">
                <label for="{module.name}">{module.display_name} <a href="#{module.name}-config" id="{module.name}-config-link" style="display:none;">(configure)</a></label>
            </div>
        """
    module_sections += "</div>"

# Add module configuration sections

all_modules_ordered_by_type = sorted(available_modules, key=lambda x: (MODULE_TYPES.index(x.type[0]), not x.requires_setup))

module_configs = ""

for module in all_modules_ordered_by_type:
    if not module.configs:
        continue
    module_configs += f"<div id='{module.name}-config' class='module-config'><h3>{module.display_name} Configuration</h3>"
    for option, value in module.configs.items():
        # create a human readable label
        option = option.replace('_', ' ').title()

        # type - if value has 'choices', then it's a select
        module_configs += "<div class='config-option'>"
        if 'choices' in value:
            module_configs += f"""
                    <label for="{module.name}-{option}">{option}</label>
                    <select id="{module.name}-{option}" name="{module.name}-{option}">
            """
            for choice in value['choices']:
                module_configs += f"<option value='{choice}'>{choice}</option>"
            module_configs += "</select>"
        elif value.get('type') == 'bool' or isinstance(value.get('default', None), bool):
            module_configs += f"""
                    <input type="checkbox" id="{module.name}-{option}" name="{module.name}-{option}">
                    <label for="{module.name}-{option}">{option}</label>
            """
        else:
            module_configs += f"""
                    <label for="{module.name}-{option}">{option}</label>
                    <input type="text" id="{module.name}-{option}" name="{module.name}-{option}">
            """
        # add help text
        if 'help' in value:
            module_configs += f"<div class='help'>{value.get('help')}</div>"
        module_configs += "</div>"
    module_configs += "</div>"

# format the settings.html jinja page with the module sections and module configuration sections
settings_page = "settings.html"
template_loader = jinja2.FileSystemLoader(searchpath="./")
template_env = jinja2.Environment(loader=template_loader)
template = template_env.get_template(settings_page)
html_content = template.render(module_sections=module_sections, module_configs=module_configs)

# Write HTML content to file
output_file = '/Users/patrick/Developer/auto-archiver/scripts/settings_page.html'
with open(output_file, 'w') as file:
    file.write(html_content)

print(f"Settings page generated at {output_file}")