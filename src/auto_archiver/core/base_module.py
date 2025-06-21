from __future__ import annotations

from typing import Mapping, Any, TYPE_CHECKING
from abc import ABC
from copy import deepcopy
from tempfile import TemporaryDirectory
from auto_archiver.utils import url as UrlUtil
from auto_archiver.core.consts import MODULE_TYPES as CONF_MODULE_TYPES

from auto_archiver.utils.custom_logger import logger

if TYPE_CHECKING:
    from .module import ModuleFactory


class BaseModule(ABC):
    """
    Base module class. All modules should inherit from this class.

    The exact methods a class implements will depend on the type of module it is,
    however modules can have a .setup() method to run any setup code
    (e.g. logging in to a site, spinning up a browser etc.)

    See consts.MODULE_TYPES for the types of modules you can create, noting that
    a subclass can be of multiple types. For example, a module that extracts data from
    a website and stores it in a database would be both an 'extractor' and a 'database' module.

    Each module is a python package, and should have a __manifest__.py file in the
    same directory as the module file. The __manifest__.py specifies the module information
    like name, author, version, dependencies etc. See DEFAULT_MANIFEST for the
    default manifest structure.

    """

    MODULE_TYPES = CONF_MODULE_TYPES

    # NOTE: these here are declard as class variables, but they are overridden by the instance variables in the __init__ method
    config: Mapping[str, Any]
    authentication: Mapping[str, Mapping[str, str]]
    name: str
    module_factory: ModuleFactory

    # this is set by the orchestrator prior to archiving
    tmp_dir: TemporaryDirectory = None

    @property
    def storages(self) -> list:
        return self.config.get("storages", [])

    def config_setup(self, config: dict):
        # this is important. Each instance is given its own deepcopied config, so modules cannot
        # change values to affect other modules
        config = deepcopy(config)
        authentication = deepcopy(config.pop("authentication", {}))

        self.authentication = authentication
        self.config = config
        for key, val in config.get(self.name, {}).items():
            setattr(self, key, val)

    def setup(self):
        # For any additional setup required by modules outside of the configs in the manifesst,
        # e.g. authentication
        pass

    def auth_for_site(self, site: str, extract_cookies=True) -> Mapping[str, Any]:
        """
        Returns the authentication information for a given site. This is used to authenticate
        with a site before extracting data. The site should be the domain of the site, e.g. 'twitter.com'

        :param site: the domain of the site to get authentication information for
        :param extract_cookies: whether or not to extract cookies from the given browser/file and return the cookie jar (disabling can speed up processing if you don't actually need the cookies jar).

        :returns: authdict dict -> {
            "username": str,
            "password": str,
            "api_key": str,
            "api_secret": str,
            "cookie": str,
            "cookies_file": str,
            "cookies_from_browser": str,
            "cookies_jar": CookieJar
        }

        **Global options:**\n
        * cookies_from_browser: str - the name of the browser to extract cookies from (e.g. 'chrome', 'firefox' - uses ytdlp under the hood to extract\n
        * cookies_file: str - the path to a cookies file to use for login\n

        **Currently, the sites dict can have keys of the following types:**\n
        * username: str - the username to use for login\n
        * password: str - the password to use for login\n
        * api_key: str - the API key to use for login\n
        * api_secret: str - the API secret to use for login\n
        * cookie: str - a cookie string to use for login (specific to this site)\n
        * cookies_file: str - the path to a cookies file to use for login (specific to this site)\n
        * cookies_from_browser: str - the name of the browser to extract cookies from (specitic for this site)\n

        """
        # TODO: think about if/how we can deal with sites that have multiple domains (main one is x.com/twitter.com)
        # for now the user must enter them both, like "x.com,twitter.com" in their config. Maybe we just hard-code?
        domain = UrlUtil.domain_for_url(site).removeprefix("www.")
        # add the 'www' version of the site to the list of sites to check
        authdict = {}

        for to_try in [site, domain, f"www.{domain}"]:
            if to_try in self.authentication:
                authdict.update(self.authentication[to_try])
                break

        # do a fuzzy string match just to print a warning - don't use it since it's insecure
        if not authdict:
            for key in self.authentication.keys():
                if key in domain or domain in key:
                    logger.debug(
                        f"Could not find exact authentication information for '{domain}'. \
did find information for '{key}' which is close, is this what you meant? \
If so, edit your authentication settings to make sure it exactly matches."
                    )

        def get_ytdlp_cookiejar(args):
            import yt_dlp
            from yt_dlp import parse_options

            logger.debug(f"Extracting cookies from settings: {args[1]}")
            # parse_options returns a named tuple as follows, we only need the ydl_options part
            # collections.namedtuple('ParsedOptions', ('parser', 'options', 'urls', 'ydl_opts'))
            ytdlp_opts = getattr(parse_options(args), "ydl_opts")
            return yt_dlp.YoutubeDL(ytdlp_opts).cookiejar

        get_cookiejar_options = None

        # order of priority:
        # 1. cookies_from_browser setting in site config
        # 2. cookies_file setting in site config
        # 3. cookies_from_browser setting in global config
        # 4. cookies_file setting in global config

        if "cookies_from_browser" in authdict:
            get_cookiejar_options = ["--cookies-from-browser", authdict["cookies_from_browser"]]
        elif "cookies_file" in authdict:
            get_cookiejar_options = ["--cookies", authdict["cookies_file"]]
        elif "cookies_from_browser" in self.authentication:
            authdict["cookies_from_browser"] = self.authentication["cookies_from_browser"]
            get_cookiejar_options = ["--cookies-from-browser", self.authentication["cookies_from_browser"]]
        elif "cookies_file" in self.authentication:
            authdict["cookies_file"] = self.authentication["cookies_file"]
            get_cookiejar_options = ["--cookies", self.authentication["cookies_file"]]

        if get_cookiejar_options:
            authdict["cookies_jar"] = get_ytdlp_cookiejar(get_cookiejar_options)

        return authdict

    def repr(self):
        return f"Module<'{self.display_name}' (config: {self.config[self.name]})>"
