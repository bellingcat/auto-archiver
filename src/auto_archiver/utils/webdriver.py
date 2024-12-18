from __future__ import annotations
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.common.print_page_options import PrintOptions

from loguru import logger
from selenium.webdriver.common.by import By
import time


class Webdriver:
    def __init__(self, width: int, height: int, timeout_seconds: int, facebook_accept_cookies: bool = False, http_proxy: str = "", print_options: dict = {}) -> webdriver:
        self.width = width
        self.height = height
        self.timeout_seconds = timeout_seconds
        self.facebook_accept_cookies = facebook_accept_cookies
        self.http_proxy = http_proxy
        # create and set print options
        self.print_options = PrintOptions()
        for k, v in print_options.items():
            setattr(self.print_options, k, v)

    def __enter__(self) -> webdriver:
        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        options.add_argument(f'--proxy-server={self.http_proxy}')
        options.set_preference('network.protocol-handler.external.tg', False)
        try:
            self.driver = webdriver.Firefox(options=options)
            self.driver.set_window_size(self.width, self.height)
            self.driver.set_page_load_timeout(self.timeout_seconds)
            self.driver.print_options = self.print_options
        except TimeoutException as e:
            logger.error(f"failed to get new webdriver, possibly due to insufficient system resources or timeout settings: {e}")

        if self.facebook_accept_cookies:
            try:
                logger.debug(f'Trying fb click accept cookie popup.')
                self.driver.get("http://www.facebook.com")
                foo = self.driver.find_element(By.XPATH, "//button[@data-cookiebanner='accept_only_essential_button']")
                foo.click()
                logger.debug(f'fb click worked')
                # linux server needs a sleep otherwise facebook cookie won't have worked and we'll get a popup on next page
                time.sleep(2)
            except:
                logger.warning(f'Failed on fb accept cookies.')

        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.close()
        self.driver.quit()
        del self.driver
        return True
