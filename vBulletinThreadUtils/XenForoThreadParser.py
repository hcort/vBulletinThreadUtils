"""
    Parses a thread from a XenForo website
"""
import re
import urllib

import requests
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from vBulletinThreadUtils import MessageFilter, MessageProcessor, ProgressVisor, vBulletinSession
from vBulletinThreadUtils.utils import get_attribute_from_soup_find, get_string_from_regex, get_soup_requests
from vBulletinThreadUtils.vBulletinLoginSelenium import hijack_cookies, create_driver_and_login


def _xenforo_wait_cookies_and_click(driver: WebDriver) -> None:
    try:
        cookie_button = expected_conditions.presence_of_element_located(
            (By.XPATH, '//*[@id="qc-cmp2-ui"]/div[2]/div/button[2]/span'))
        WebDriverWait(driver, timeout=20).until(cookie_button)
        cookie_button = driver.find_element(By.XPATH, '//*[@id="qc-cmp2-ui"]/div[2]/div/button[2]/span')
        cookie_button.click()
    except Exception as err:
        print(f'Error clicking cookies button: {err}')


def _xenforo_login_and_wait(driver: WebDriver, login_url: str, login_data: dict) -> None:
    timeout = 20
    try:
        driver.get(login_url)
        _xenforo_wait_cookies_and_click(driver)
        login_input = driver.find_element(By.NAME, 'login')
        login_input.send_keys(login_data.get('vb_login_username', ''))
        password_input = driver.find_element(By.NAME, 'password')
        password_input.send_keys(login_data.get('vb_login_password', ''))
        password_input.send_keys(Keys.RETURN)
        logged_in_username = expected_conditions.presence_of_element_located(
            (By.CLASS_NAME, 'p-navgroup--member'))
        WebDriverWait(driver, timeout).until(logged_in_username)
    except Exception as err:
        print(f'Error login to {login_url} - {err}')


def _xenforo_check_logged_in(driver: WebDriver) -> bool:
    try:
        logged_in_username = expected_conditions.presence_of_element_located(
            (By.CLASS_NAME, 'p-navgroup--member'))
        WebDriverWait(driver, timeout=20).until(logged_in_username)
        return True
    except TimeoutException:
        return False


def xenforo_login_selenium(login_url: str = None, login_data: dict = None) -> requests.Session | None:
    if not login_url or not login_data:
        return None
    vBulletinSession.user_name = login_data.get('vb_login_username', '')
    vBulletinSession.password = login_data.get('vb_login_password', '')
    # selenium.common.exceptions.WebDriverException: Message: Service geckodriver unexpectedly exited. Status code
    # was: 64 miro geckodriver.log geckodriver: error: Found argument '--websocket-port' which wasn't expected,
    # or isn't valid in this context > actualizar geckodriver https://stackoverflow.com/a/70822145/4105601
    try:
        driver = create_driver_and_login(
            login_url=login_url,
            login_data=login_data,
            login_function=_xenforo_login_and_wait,
            check_logged_function=_xenforo_check_logged_in,
            click_cookies_function=_xenforo_wait_cookies_and_click
        )
        s = hijack_cookies(driver)
        driver.close()
        return s
    except TimeoutException as ex:
        print(f'Error accessing {login_url}: Timeout: {str(ex)}')
    except Exception as ex:
        print(f'Error accessing {login_url}: Unknown error: {str(ex)}')
    return None


regex_thread_id_url = re.compile(r'/threads/(.+)/')
regex_thread_page_number = re.compile(r'/page-([0-9]+)')


def update_progress_bar(progress, soup):
    if progress:
        if not progress.total:
            progress.total = int(soup.select_one('ul.pageNav-main>li.pageNav-page:last-child').text)
        progress.update()


regex_post_id = re.compile(r'/post\-([0-9]+)')


def _parse_page(soup, thread_info, filter_obj, current_url, post_processor):
    all_message_indexes = soup.select(
        'header.message-attribution > ul:nth-child(2) > li:nth-child(3) > a:nth-child(1)')
    all_messages = soup.select('article.message-body > div.bbWrapper')
    all_dates = soup.select('div.message-attribution-main>a>time.u-dt')
    all_user_info = soup.select('h4.message-name>a.username')
    all_avatars = soup.select('a.avatar>img')
    try:
        for idx, msg, post_date, user_info, avatar in zip(all_message_indexes,
                                                               all_messages,
                                                               all_dates,
                                                               all_user_info,
                                                               all_avatars):

            message_as_dict = {
                'author': {
                    'id': user_info.get('data-user-id', ''),
                    'username': user_info.text,
                    'avatar': avatar.get('src', ''),
                    'is_op': (user_info.get('data-user-id', '') == thread_info['author_id'])
                },
                'index': int(idx.text.strip().replace('#', '').replace('.', '')),
                'date': post_date.get('datetime', ''),
                'link': idx.get('href', ''),
                'title': ''
            }
            message_id = get_string_from_regex(regex_post_id, message_as_dict['link'])
            saved_message = msg if not post_processor else \
                post_processor.process_message(thread_info=thread_info, post_id=message_id, message=msg)
            message_as_dict['message'] = saved_message

            if (not filter_obj) or (filter_obj and (filter_obj.filter_message(message_id, message_as_dict))):
                thread_info['parsed_messages'][message_id] = message_as_dict

            thread_info['last_message'] = message_id
            thread_info['modification_date'] = message_as_dict['date']
            thread_info['message_count'] = message_as_dict['index']
    except Exception as err:
        print(f'Error parsing {current_url} - {err}')


def parse_thread_xenforo(session: requests.Session,
                         thread_info: dict,
                         filter_obj: MessageFilter = None,
                         post_processor: MessageProcessor = None,
                         progress: ProgressVisor = None):
    """

    :param session: a Requests session object
                in vbulletin the session is stored in a VBulletinSession object
    :param thread_info: see vBulletinThreadParserGen documentation
                this object can contain the messages already parsed in this thread. In that case only new messages
                will be parsed and added
    :param filter_obj: determines if a message is stored in thread_info or not
                see MessageFilter.py
    :param post_processor: takes the raw message and returns the data that will be stored in thread_info
                see MessageProcessor.py
    :param progress: a ProgressVisor object that can show a progress bar for the parser
    :return: there is no return value. Parsed data is stored in new keys inside thread_info


    """
    if not session:
        return
    first_url = thread_info.get('last_page', None)
    if not first_url:
        first_url = thread_info['url']
    if progress and thread_info['last_page']:
        progress.update(n=int(
            get_string_from_regex(regex_thread_page_number, thread_info['last_page']))
        )
    url_parts = urllib.parse.urlparse(first_url)
    base_url = f'{url_parts.scheme}://{url_parts.hostname}'
    current_url = url_parts.path
    while current_url:
        full_url = base_url + current_url
        soup = get_soup_requests(session, full_url)
        if not soup:
            print(f'Error getting {current_url}')
        update_progress_bar(progress, soup)
        _initialize_thread_info(thread_info, soup)
        _parse_page(soup, thread_info, filter_obj, current_url, post_processor)
        thread_info['last_page'] = current_url
        current_url = get_attribute_from_soup_find(soup=soup,
                                                   what_to_find='a',
                                                   find_attrs={'class': 'pageNav-jump--next'},
                                                   attribute='href')


def _initialize_thread_info(thread_info, soup):
    if not thread_info.get('title', None):
        thread_info['title'] = soup.select_one('h1.p-title-value').text
        # FIXME fix date formats
        thread_info['date'] = soup.select_one('time.u-dt').get('datetime', '')
        author_info = soup.select_one('a.username.u-concealed')
        if author_info:
            thread_info['author'] = author_info.text
            thread_info['author_id'] = author_info.get('data-user-id', '')
        # thread_info['id'] = regex_thread_id_url.search(thread_info['url']).groups(0)[-1].split('.')[-1]
        thread_info['id'] = get_string_from_regex(regex_thread_id_url, thread_info['url']).split('.')[-1]
        # thread_info['hover'] = soup.find('meta', {'property': 'og:description'}).get('content', '')
        thread_info['hover'] = get_attribute_from_soup_find(soup=soup,
                                                            what_to_find='meta',
                                                            find_attrs={'property': 'og:description'},
                                                            attribute='content',
                                                            default_value='')
        # thread_info['first_post_id'] = soup.find_all('article', {'class': 'message'})[0].get('id').split('-')[-1]
        thread_info['first_post_id'] = get_attribute_from_soup_find(soup=soup,
                                                                    what_to_find='article',
                                                                    find_attrs={'class': 'message'},
                                                                    attribute='id',
                                                                    default_value='').split('-')[-1]
        thread_info['creation_date'] = thread_info['date']
        thread_info['modification_date'] = ''
        thread_info['message_count'] = 0
        thread_info['parsed_messages'] = {}
