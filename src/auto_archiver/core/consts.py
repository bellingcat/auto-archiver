class SetupError(ValueError):
    pass


MODULE_TYPES = ["feeder", "extractor", "enricher", "database", "storage", "formatter"]

MANIFEST_FILE = "__manifest__.py"

DEFAULT_MANIFEST = {
    "name": "",  # the display name of the module
    "author": "Bellingcat",  # creator of the module, leave this as Bellingcat or set your own name!
    "type": [],  # the type of the module, can be one or more of MODULE_TYPES
    "requires_setup": True,  # whether or not this module requires additional setup such as setting API Keys or installing additional software
    "description": "",  # a description of the module
    "dependencies": {},  # external dependencies, e.g. python packages or binaries, in dictionary format
    "entry_point": "",  # the entry point for the module, in the format 'module_name::ClassName'. This can be left blank to use the default entry point of module_name::ModuleName
    "version": "1.0",  # the version of the module
    "configs": {},  # any configuration options this module has, these will be exposed to the user in the config file or via the command line
}
