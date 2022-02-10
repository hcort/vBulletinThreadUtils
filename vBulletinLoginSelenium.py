import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests


def test_requests(driver, current_url):
    headers = {
        "User-Agent":
            "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36"
    }
    s = requests.session()
    s.headers.update(headers)

    for cookie in driver.get_cookies():
        c = {cookie['name']: cookie['value']}
        s.cookies.update(c)

    # driver.close()

    current_page = s.get(current_url)
    if current_page.status_code != requests.codes.ok:
        return
    soup = BeautifulSoup(current_page.text, features="html.parser")
    regex_id = re.compile("edit([0-9]{9})")
    all_posts = soup.find_all('div', id=regex_id, recursive=True)
    if all_posts:
        print('Encuentro posts')


def VBulletinLoginSelenium(login_url='', login_data={}):
    driver = webdriver.Firefox()
    # selenium.common.exceptions.WebDriverException: Message: Service geckodriver unexpectedly exited. Status code
    # was: 64 miro geckodriver.log geckodriver: error: Found argument '--websocket-port' which wasn't expected,
    # or isn't valid in this context > actualizar geckodriver https://stackoverflow.com/a/70822145/4105601
    login_url_2 = 'https://www.forocoches.com/foro/'
    driver.get(login_url_2)
    element = driver.find_element(By.ID, "navbar_username")
    element.send_keys(login_data['vb_login_username'])
    element = driver.find_element(By.ID, "navbar_password")
    element.send_keys(login_data['vb_login_password'])
    element.send_keys(Keys.RETURN)
    timeout = 1000
    element_present = EC.presence_of_element_located((By.LINK_TEXT, login_data['vb_login_username']))
    WebDriverWait(driver, timeout).until(element_present)
    headers = {
        "User-Agent":
            "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36"
    }
    s = requests.session()
    s.headers.update(headers)

    for cookie in driver.get_cookies():
        c = {cookie['name']: cookie['value']}
        s.cookies.update(c)

    driver.close()
    cookie_bbimloggedin = s.cookies.get('bbimloggedin', default='no')
    if cookie_bbimloggedin == 'no':
        print('cookie bbimloggedin no encontrada')
    return s