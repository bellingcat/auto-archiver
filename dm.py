from selenium import webdriver
import time
from selenium.webdriver.common.by import By

options = webdriver.FirefoxOptions()
options.headless = True
driver = webdriver.Firefox(options=options)
driver.set_window_size(1400, 2000)

# fonts showing up as boxes with numbers
driver.get("https://www.kanbawzatainews.com/2021/09/mytel_25.html")
# driver.get("http://www.chinatoday.com.cn/")

# click the button: Allow Essential and Optioanl Cookies
# foo = driver.find_element(By.XPATH,"//button[@data-cookiebanner='accept_only_essential_button']")
# foo.click()

# # Search & Enter the Email or Phone field & Enter Password
# username = driver.find_element(By.ID,"email")
# password = driver.find_element(By.ID,"pass")
# submit = driver.find_element(By.NAME,"login")

# username.send_keys("test@gmail.com")
# password.send_keys("password")

# # Click Login
# submit.click()

# # now am logged in, go to original page
# driver.get("https://www.facebook.com/watch/?v=343188674422293")
time.sleep(1)

# save a screenshot
driver.save_screenshot("screenshot.png")