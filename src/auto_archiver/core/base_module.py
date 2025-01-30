

from urllib.parse import urlparse
from typing import  Mapping, Any
from abc import ABC
from copy import deepcopy, copy
from tempfile import TemporaryDirectory

from loguru import logger

class BaseModule(ABC):

    """
    Base module class. All modules should inherit from this class.

    The exact methods a class implements will depend on the type of module it is,
    however all modules have a .setup(config: dict) method to run any setup code
    (e.g. logging in to a site, spinning up a browser etc.)

    See BaseModule.MODULE_TYPES for the types of modules you can create, noting that
    a subclass can be of multiple types. For example, a module that extracts data from
    a website and stores it in a database would be both an 'extractor' and a 'database' module.

    Each module is a python package, and should have a __manifest__.py file in the
    same directory as the module file. The __manifest__.py specifies the module information
    like name, author, version, dependencies etc. See BaseModule._DEFAULT_MANIFEST for the
    default manifest structure.

    """

    MODULE_TYPES = [
        'feeder',
        'extractor',
        'enricher',
        'database',
        'storage',
        'formatter'
    ]

    _DEFAULT_MANIFEST = {
    'name': '', # the display name of the module
    'author': 'Bellingcat', # creator of the module, leave this as Bellingcat or set your own name!
    'type': [], # the type of the module, can be one or more of BaseModule.MODULE_TYPES
    'requires_setup': True, # whether or not this module requires additional setup such as setting API Keys or installing additional softare
    'description': '', # a description of the module
    'dependencies': {}, # external dependencies, e.g. python packages or binaries, in dictionary format
    'entry_point': '', # the entry point for the module, in the format 'module_name::ClassName'. This can be left blank to use the default entry point of module_name::ModuleName
    'version': '1.0', # the version of the module
    'configs': {} # any configuration options this module has, these will be exposed to the user in the config file or via the command line
}

    config: Mapping[str, Any]
    authentication: Mapping[str, Mapping[str, str]]
    name: str

    # this is set by the orchestrator prior to archiving
    tmp_dir: TemporaryDirectory = None

    def setup(self, config: dict):

        authentication = config.get('authentication', {})
        # extract out contatenated sites
        for key, val in copy(authentication).items():
            if "," in key:
                for site in key.split(","):
                    authentication[site] = val
                del authentication[key]

        # this is important. Each instance is given its own deepcopied config, so modules cannot
        # change values to affect other modules
        config = deepcopy(config)
        authentication = deepcopy(config.pop('authentication', {}))

        self.authentication = authentication
        self.config = config
        for key, val in config.get(self.name, {}).items():
            setattr(self, key, val)

    def repr(self):
        return f"Module<'{self.display_name}' (config: {self.config[self.name]})>"
    
    def auth_for_site(self, site: str) -> dict:
        # TODO: think about if/how we can deal with sites that have multiple domains (main one is x.com/twitter.com)
        # for now, just hard code those.

        # SECURITY: parse the domain using urllib
        site = urlparse(site).netloc
        # add the 'www' version of the site to the list of sites to check
        for to_try in [site, f"www.{site}"]:
            if to_try in self.authentication:
                return self.authentication[to_try]

        # do a fuzzy string match just to print a warning - don't use it since it's insecure
        for key in self.authentication.keys():
            if key in site or site in key:
                logger.warning(f"Could not find exact authentication information for site '{site}'. \
                                did find information for '{key}' which is close, is this what you meant? \
                                If so, edit your authentication settings to make sure it exactly matches.")
        
        return {}