""" This Webdriver class acts as a context manager for the selenium webdriver. """
from __future__ import annotations
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.common.print_page_options import PrintOptions

from loguru import logger
from selenium.webdriver.common.by import By
import time

#import domain_for_url
from urllib.parse import urlparse, urlunparse
from http.cookiejar import MozillaCookieJar

class CookieSettingDriver(webdriver.Firefox):

    facebook_accept_cookies: bool
    cookies: str
    cookiejar: MozillaCookieJar

    def __init__(self, cookies, cookiejar, facebook_accept_cookies, *args, **kwargs):
        super(CookieSettingDriver, self).__init__(*args, **kwargs)
        self.cookies = cookies
        self.cookiejar = cookiejar
        self.facebook_accept_cookies = facebook_accept_cookies

    def get(self, url: str):
        if self.cookies or self.cookiejar:
            # set up the driver to make it not 'cookie averse' (needs a context/URL)
            # get the 'robots.txt' file which should be quick and easy
            robots_url = urlunparse(urlparse(url)._replace(path='/robots.txt', query='', fragment=''))
            super(CookieSettingDriver, self).get(robots_url)

            if self.cookies:
                # an explicit cookie is set for this site, use that first
                for cookie in self.cookies.split(";"):
                    for name, value in cookie.split("="):
                        self.driver.add_cookie({'name': name, 'value': value})
            elif self.cookiejar:
                domain = urlparse(url).netloc.lstrip("www.")
                for cookie in self.cookiejar:
                    if domain in cookie.domain:
                        try:
                            self.add_cookie({
                                'name': cookie.name,
                                'value': cookie.value,
                                'path': cookie.path,
                                'domain': cookie.domain,
                                'secure': bool(cookie.secure),
                                'expiry': cookie.expires
                            })
                        except Exception as e:
                            logger.warning(f"Failed to add cookie to webdriver: {e}")
        
        if self.facebook_accept_cookies:
            try:
                logger.debug(f'Trying fb click accept cookie popup.')
                super(CookieSettingDriver, self).get("http://www.facebook.com")
                essential_only = self.find_element(By.XPATH, "//span[contains(text(), 'Decline optional cookies')]")
                essential_only.click()
                logger.debug(f'fb click worked')
                # linux server needs a sleep otherwise facebook cookie won't have worked and we'll get a popup on next page
                time.sleep(2)
            except Exception as e:
                logger.warning(f'Failed on fb accept cookies.', e)
        # now get the actual URL
        super(CookieSettingDriver, self).get(url)
    
class Webdriver:
    def __init__(self, width: int, height: int, timeout_seconds: int,
                 facebook_accept_cookies: bool = False, http_proxy: str = "",
                 print_options: dict = {}, auth: dict = {}) -> webdriver:
        self.width = width
        self.height = height
        self.timeout_seconds = timeout_seconds
        self.auth = auth
        self.facebook_accept_cookies = facebook_accept_cookies
        self.http_proxy = http_proxy
        # create and set print options
        self.print_options = PrintOptions()
        for k, v in print_options.items():
            setattr(self.print_options, k, v)

    def __enter__(self) -> webdriver:

        options = webdriver.FirefoxOptions()
        # options.add_argument("--headless")
        options.add_argument(f'--proxy-server={self.http_proxy}')
        options.set_preference('network.protocol-handler.external.tg', False)
        # if facebook cookie popup is present, force the browser to English since then it's easier to click the 'Decline optional cookies' option
        if self.facebook_accept_cookies:
            options.add_argument('--lang=en')

        try:
            self.driver = CookieSettingDriver(cookies=self.auth.get('cookies'), cookiejar=self.auth.get('cookies_jar'),
                                              facebook_accept_cookies=self.facebook_accept_cookies, options=options)
            self.driver.set_window_size(self.width, self.height)
            self.driver.set_page_load_timeout(self.timeout_seconds)
            self.driver.print_options = self.print_options
        except TimeoutException as e:
            logger.error(f"failed to get new webdriver, possibly due to insufficient system resources or timeout settings: {e}")

        return self.driver
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.close()
        self.driver.quit()
        del self.driver
        return True
