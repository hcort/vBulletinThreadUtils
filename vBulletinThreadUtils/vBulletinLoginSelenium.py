import os

import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def create_session_object():
    headers = {
        "User-Agent":
            "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 "
            "Safari/537.36 "
    }
    s = requests.session()
    s.headers.update(headers)
    return s


def VBulletinLogin(login_url='', login_data={}):
    return VBulletinLoginSelenium(login_url=login_url, login_data=login_data)


def do_login_and_wait(driver, login_url, login_data):
    driver.get(login_url)
    element = driver.find_element(By.NAME, "vb_login_username")
    element.send_keys(login_data.get('vb_login_username', ''))
    element = driver.find_element(By.NAME, "vb_login_password")
    element.send_keys(login_data.get('vb_login_password', ''))
    element.send_keys(Keys.RETURN)
    timeout = 100
    element_present = EC.presence_of_element_located((By.ID, "AutoNumber1"))
    WebDriverWait(driver, timeout).until(element_present)


def hijack_cookies(driver):
    s = create_session_object()
    for cookie in driver.get_cookies():
        c = {cookie['name']: cookie['value']}
        s.cookies.update(c)
    return s


def get_logged_in_cookie(driver):
    for cookie in driver.get_cookies():
        if cookie['name'] == 'bbimloggedin':
            return cookie['value']
    return 'no'


def click_cookies_button(driver):
    timeout = 100
    element_present = EC.presence_of_element_located((By.CLASS_NAME, 'sd-cmp-3cRQ2'))
    WebDriverWait(driver, timeout).until(element_present)
    element = driver.find_element(By.CLASS_NAME, 'sd-cmp-3cRQ2')
    element.click()
    element_present = EC.presence_of_element_located((By.CLASS_NAME, 'sd-cmp-3cRQ2'))
    WebDriverWait(driver, timeout).until_not(element_present)


def VBulletinLoginSelenium(login_url='', login_data=None):
    """
    :param login_url: the url with the login form
    :param login_data: all the login data we need
    :return: This method returs a Requests session in which we put the cookies extracted from Selenium

        The Selenium driver is closed after getting the cookies, as we proceed to the parsing+
        using Requests and Beautiful Soup
    """
    s = None
    if not login_url or not login_data:
        return None
    try:
        driver = create_driver_and_login(login_url, login_data)
        if driver:
            s = hijack_cookies(driver)
            cookie_bbimloggedin = s.cookies.get('bbimloggedin', default='no')
            if cookie_bbimloggedin == 'no':
                print('cookie bbimloggedin no encontrada')
    finally:
        driver.close()
    return s


def create_driver_and_login(login_url='', login_data=None, webdriver_type='firefox'):
    """
    :param login_url: the url with the login form
    :param login_data: all the login data we need
    :return: This method logs in into the forum and then returns the Selenium driver
    """
    if not login_url or not login_data:
        return None
    if webdriver_type == 'firefox':
        # os.environ['MOZ_HEADLESS'] = '1'
        driver = webdriver.Firefox()
    elif webdriver_type == 'opera':
        # https://stackoverflow.com/questions/55130791/how-to-enable-built-in-vpn-in-operadriver
        # I use my user profile where I have activated the VPN
        opera_profile = r'C:\Users\Héctor\AppData\Roaming\Opera Software\Opera Stable'
        options = webdriver.ChromeOptions()
        options.add_argument('user-data-dir=' + opera_profile)
        # options._binary_location = r'C:\Users\Héctor\AppData\Local\Programs\Opera\\opera.exe'
        driver = webdriver.Opera(options=options)
    else:
        exit('Unknown webdriver option')
    do_login_and_wait(driver, login_url, login_data)
    if get_logged_in_cookie(driver) != 'yes':
        print('cookie bbimloggedin no encontrada')
        driver.close()
        return None
    click_cookies_button(driver)
    return driver


def test_driver():
    driver = webdriver.Firefox()
    try:
        driver.get('about:blank')
    except TimeoutException as ex:
        print(f'Error {str(ex)}')
    finally:
        driver.close()
