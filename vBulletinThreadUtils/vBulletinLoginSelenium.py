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


def VBulletinLoginSelenium(login_url='', login_data=None):
    if not login_url or not login_data:
        return None
    driver = webdriver.Firefox()
    s = None
    # selenium.common.exceptions.WebDriverException: Message: Service geckodriver unexpectedly exited. Status code
    # was: 64 miro geckodriver.log geckodriver: error: Found argument '--websocket-port' which wasn't expected,
    # or isn't valid in this context > actualizar geckodriver https://stackoverflow.com/a/70822145/4105601
    try:
        driver.get(login_url)
        element = driver.find_element(By.ID, "navbar_username")
        element.send_keys(login_data.get('vb_login_username', ''))
        element = driver.find_element(By.ID, "navbar_password")
        element.send_keys(login_data.get('vb_login_password', ''))
        element.send_keys(Keys.RETURN)
        timeout = 100
        element_present = EC.presence_of_element_located((By.LINK_TEXT, login_data.get('vb_login_username', '')))
        WebDriverWait(driver, timeout).until(element_present)
        s = create_session_object()
        for cookie in driver.get_cookies():
            c = {cookie['name']: cookie['value']}
            s.cookies.update(c)
        cookie_bbimloggedin = s.cookies.get('bbimloggedin', default='no')
        if cookie_bbimloggedin == 'no':
            print('cookie bbimloggedin no encontrada')
    except TimeoutException as ex:
        print('Error accessing {}: Timeout: {}'.format(login_url, str(ex)))
    finally:
        driver.close()
    return s
