"""This Webdriver class acts as a context manager for the selenium webdriver."""

from __future__ import annotations

import os
import time
import re

# import domain_for_url
from urllib.parse import urlparse, urlunparse
from http.cookiejar import MozillaCookieJar

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common import exceptions as selenium_exceptions
from selenium.webdriver.common.print_page_options import PrintOptions
from selenium.webdriver.common.by import By

from loguru import logger


class CookieSettingDriver(webdriver.Firefox):
    facebook_accept_cookies: bool
    cookie: str
    cookie_jar: MozillaCookieJar

    def __init__(self, cookie, cookie_jar, facebook_accept_cookies, *args, **kwargs):
        if os.environ.get("RUNNING_IN_DOCKER"):
            # Selenium doesn't support linux-aarch64 driver, we need to set this manually
            kwargs["service"] = webdriver.FirefoxService(executable_path="/usr/local/bin/geckodriver")

        super(CookieSettingDriver, self).__init__(*args, **kwargs)
        self.cookie = cookie
        self.cookie_jar = cookie_jar
        self.facebook_accept_cookies = facebook_accept_cookies

    def get(self, url: str):
        if self.cookie_jar or self.cookie:
            # set up the driver to make it not 'cookie averse' (needs a context/URL)
            # get the 'robots.txt' file which should be quick and easy
            robots_url = urlunparse(urlparse(url)._replace(path="/robots.txt", query="", fragment=""))
            super(CookieSettingDriver, self).get(robots_url)

            if self.cookie:
                # an explicit cookie is set for this site, use that first
                for cookie in self.cookies.split(";"):
                    for name, value in cookie.split("="):
                        self.driver.add_cookie({"name": name, "value": value})
            elif self.cookie_jar:
                domain = urlparse(url).netloc.removeprefix("www.")
                regex = re.compile(f"(www)?.?{domain}$")
                for cookie in self.cookie_jar:
                    if regex.match(cookie.domain):
                        try:
                            self.add_cookie(
                                {
                                    "name": cookie.name,
                                    "value": cookie.value,
                                    "path": cookie.path,
                                    "domain": cookie.domain,
                                    "secure": bool(cookie.secure),
                                    "expiry": cookie.expires,
                                }
                            )
                        except Exception as e:
                            logger.warning(f"Failed to add cookie ({cookie.domain}) to webdriver for url {domain}: {e}")

        super(CookieSettingDriver, self).get(url)
        time.sleep(2)

        # Try and use some common button text to reject/accept cookies
        for text in [
            "Refuse non-essential cookies",
            "Decline optional cookies",
            "Reject additional cookies",
            "Reject all",
            "Accept all cookies",
        ]:
            try:
                xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
                self.find_element(By.XPATH, xpath).click()
                time.sleep(2)
            except selenium_exceptions.NoSuchElementException:
                pass

        # now get the actual URL
        if self.facebook_accept_cookies:
            # try and click the 'close' button on the 'login' window to close it
            try:
                xpath = "//div[@role='dialog']//div[@aria-label='Close']"
                self.find_element(By.XPATH, xpath).click()
                time.sleep(2)
            except selenium_exceptions.NoSuchElementException:
                logger.warning("Unable to find the 'close' button on the facebook login window")
                pass

        else:
            # for all other sites, try and use some common button text to reject/accept cookies
            for text in [
                "Refuse non-essential cookies",
                "Decline optional cookies",
                "Reject additional cookies",
                "Reject all",
                "Accept all cookies",
            ]:
                try:
                    xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
                    WebDriverWait(self, 5).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
                    break
                except selenium_exceptions.WebDriverException:
                    pass


class Webdriver:
    def __init__(
        self,
        width: int,
        height: int,
        timeout_seconds: int,
        facebook_accept_cookies: bool = False,
        http_proxy: str = "",
        print_options: dict = {},
        auth: dict = {},
    ) -> webdriver:
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
        options.add_argument("--headless")
        options.add_argument(f"--proxy-server={self.http_proxy}")
        options.set_preference("network.protocol-handler.external.tg", False)
        # if facebook cookie popup is present, force the browser to English since then it's easier to click the 'Decline optional cookies' option
        if self.facebook_accept_cookies:
            options.add_argument("--lang=en")

        try:
            self.driver = CookieSettingDriver(
                cookie=self.auth.get("cookie"),
                cookie_jar=self.auth.get("cookies_jar"),
                facebook_accept_cookies=self.facebook_accept_cookies,
                options=options,
            )
            self.driver.set_window_size(self.width, self.height)
            self.driver.set_page_load_timeout(self.timeout_seconds)
            self.driver.print_options = self.print_options
        except selenium_exceptions.TimeoutException as e:
            logger.error(
                f"failed to get new webdriver, possibly due to insufficient system resources or timeout settings: {e}"
            )

        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.close()
        self.driver.quit()
        del self.driver
        return True
