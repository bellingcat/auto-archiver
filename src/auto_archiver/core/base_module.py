
from urllib.parse import urlparse
from typing import  Mapping, Any
from abc import ABC
from copy import deepcopy, copy
from tempfile import TemporaryDirectory
from auto_archiver.utils import url as UrlUtil

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

    @property
    def storages(self) -> list:
        return self.config.get('storages', [])

    def setup(self, config: dict):

        authentication = config.get('authentication', {})
        # extract out concatenated sites
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

    def module_setup(self):
        # For any additional setup required by modules, e.g. autehntication
        pass

    def auth_for_site(self, site: str, extract_cookies=True) -> Mapping[str, Any]:
        """
        Returns the authentication information for a given site. This is used to authenticate
        with a site before extracting data. The site should be the domain of the site, e.g. 'twitter.com'
        
        extract_cookies: bool - whether or not to extract cookies from the given browser and return the 
        cookie jar (disabling can speed up) processing if you don't actually need the cookies jar

        Currently, the dict can have keys of the following types:
        - username: str - the username to use for login
        - password: str - the password to use for login
        - api_key: str - the API key to use for login
        - api_secret: str - the API secret to use for login
        - cookie: str - a cookie string to use for login (specific to this site)
        - cookies_jar: YoutubeDLCookieJar | http.cookiejar.MozillaCookieJar - a cookie jar compatible with requests (e.g. `requests.get(cookies=cookie_jar)`)
        """
        # TODO: think about if/how we can deal with sites that have multiple domains (main one is x.com/twitter.com)
        # for now the user must enter them both, like "x.com,twitter.com" in their config. Maybe we just hard-code?

        site = UrlUtil.domain_for_url(site)
        # add the 'www' version of the site to the list of sites to check
        authdict = {}


        for to_try in [site, f"www.{site}"]:
            if to_try in self.authentication:
                authdict.update(self.authentication[to_try])
                break

        # do a fuzzy string match just to print a warning - don't use it since it's insecure
        if not authdict:
            for key in self.authentication.keys():
                if key in site or site in key:
                    logger.debug(f"Could not find exact authentication information for site '{site}'. \
                                    did find information for '{key}' which is close, is this what you meant? \
                                    If so, edit your authentication settings to make sure it exactly matches.")

        def get_ytdlp_cookiejar(args):
            import yt_dlp
            from yt_dlp import parse_options
            logger.debug(f"Extracting cookies from settings: {args[1]}")
            # parse_options returns a named tuple as follows, we only need the ydl_options part
            # collections.namedtuple('ParsedOptions', ('parser', 'options', 'urls', 'ydl_opts'))
            ytdlp_opts = getattr(parse_options(args), 'ydl_opts')
            return yt_dlp.YoutubeDL(ytdlp_opts).cookiejar

        # get the cookies jar, prefer the browser cookies than the file
        if 'cookies_from_browser' in self.authentication:
            authdict['cookies_from_browser'] = self.authentication['cookies_from_browser']
            if extract_cookies:
                authdict['cookies_jar'] = get_ytdlp_cookiejar(['--cookies-from-browser', self.authentication['cookies_from_browser']])
        elif 'cookies_file' in self.authentication:
            authdict['cookies_file'] = self.authentication['cookies_file']
            if extract_cookies:
                authdict['cookies_jar'] = get_ytdlp_cookiejar(['--cookies', self.authentication['cookies_file']])
        
        return authdict
    
    def repr(self):
        return f"Module<'{self.display_name}' (config: {self.config[self.name]})>"