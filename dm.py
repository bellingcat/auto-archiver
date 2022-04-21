from selenium import webdriver
import time
from selenium.webdriver.common.by import By

options = webdriver.FirefoxOptions()
options.headless = True
driver = webdriver.Firefox(options=options)
driver.set_window_size(1400, 2000)

# Navigate to Facebook
driver.get("http://www.facebook.com")

# click the button: Allow Essential and Optioanl Cookies
foo = driver.find_element(By.XPATH,"//button[@data-cookiebanner='accept_only_essential_button']")
foo.click()

# Search & Enter the Email or Phone field & Enter Password
username = driver.find_element(By.ID,"email")
password = driver.find_element(By.ID,"pass")
submit = driver.find_element(By.NAME,"login")

username.send_keys("test@gmail.com")
password.send_keys("password")

# Click Login
submit.click()

# now am logged in, go to original page
driver.get("https://www.facebook.com/watch/?v=343188674422293")
time.sleep(6)

# save a screenshot
driver.save_screenshot("screenshot.png")