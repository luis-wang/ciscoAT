#coding=utf-8
#!/usr/bin/python
'''
Created on Sep 16, 2013

@author: root
'''
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
import time


browser = webdriver.Firefox() # Get local session of firefox
browser.get("http://www.yahoo.com") # Load page

assert "Yahoo" in browser.title
print 'browser.title = ', browser.title

elem = browser.find_element_by_name("p") # Find the query box
elem.send_keys("seleniumhq" + Keys.RETURN)
time.sleep(0.2) # Let the page load, will be added to the API
try:
    browser.find_element_by_xpath("//a[contains(@href,'http://seleniumhq.org')]")
except NoSuchElementException:
    assert 0, "can't find seleniumhq"
browser.close()