"""
    Uses selenium to log into a forum

    create_driver_and_login is the main method. It can be used to log in into several websites using
    custom functions as parameters
"""
from typing import Callable

import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def create_session_object():
    headers = {
        'User-Agent':
            'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 '
            'Safari/537.36 '
    }
    s = requests.session()
    s.headers.update(headers)
    return s


def hijack_cookies(driver):
    if not driver:
        return None
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


def click_cookies_vBulletin(driver):
    try:
        timeout = 20
        element_present = EC.presence_of_element_located((By.CLASS_NAME, 'sd-cmp-3cRQ2'))
        WebDriverWait(driver, timeout).until(element_present)
        element = driver.find_element(By.CLASS_NAME, 'sd-cmp-3cRQ2')
        element.click()
        element_present = EC.presence_of_element_located((By.CLASS_NAME, 'sd-cmp-3cRQ2'))
        WebDriverWait(driver, timeout).until_not(element_present)
    except TimeoutError:
        pass


def do_login_and_wait(driver, login_url, login_data):
    driver.get(login_url)
    element = driver.find_element(By.NAME, 'vb_login_username')
    element.send_keys(login_data.get('vb_login_username', ''))
    element = driver.find_element(By.NAME, 'vb_login_password')
    element.send_keys(login_data.get('vb_login_password', ''))
    element.send_keys(Keys.RETURN)
    timeout = 100
    element_present = EC.presence_of_element_located((By.ID, 'AutoNumber1'))
    WebDriverWait(driver, timeout).until(element_present)


def check_bb_logged_in_cookie(driver):
    return get_logged_in_cookie(driver) == 'yes'


def create_driver_and_login(login_url: str = '',
                            login_data: dict = None,
                            webdriver_type: str = 'firefox',
                            login_function: Callable = do_login_and_wait,
                            check_logged_function: Callable = check_bb_logged_in_cookie,
                            click_cookies_function: Callable = click_cookies_vBulletin) -> WebDriver | None:
    """
    :param login_url: the url with the login form
    :param login_data: all the login data we need
    :param webdriver_type: we may choose between different webdrivers (TODO)
    :param click_cookies_function: function that clicks the button to accept cookies
    :param check_logged_function: function that checks if we have logged into the forum
    :param login_function: function that fills the log in form
    :return: a selenium webdriver alredy logged in or None
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
    login_function(driver, login_url, login_data)
    if not check_logged_function(driver):
        print('Failed login')
        driver.close()
        return None
    click_cookies_function(driver)
    return driver


def test_driver():
    driver = webdriver.Firefox()
    try:
        driver.get('about:blank')
    except TimeoutException as ex:
        print(f'Error {str(ex)}')
    finally:
        driver.close()
