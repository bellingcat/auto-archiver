from __future__ import annotations
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from loguru import logger
from selenium.webdriver.common.by import By
import time


class Webdriver:
    def __init__(self, width: int, height: int, timeout_seconds: int, facebook_accept_cookies: bool = False) -> webdriver:
        self.width = width
        self.height = height
        self.timeout_seconds = timeout_seconds
        self.facebook_accept_cookies = facebook_accept_cookies

    def __enter__(self) -> webdriver:
        options = webdriver.FirefoxOptions()
        options.headless = True
        options.set_preference('network.protocol-handler.external.tg', False)
        try:
            self.driver = webdriver.Firefox(options=options)
            self.driver.set_window_size(self.width, self.height)
            self.driver.set_page_load_timeout(self.timeout_seconds)
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
