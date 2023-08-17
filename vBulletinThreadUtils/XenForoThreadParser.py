from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
import re
import urllib
from urllib.parse import quote
from bs4 import BeautifulSoup

from vBulletinThreadUtils import MessageFilter, MessageProcessor, ProgressVisor
from vBulletinThreadUtils.vBulletinLoginSelenium import hijack_cookies


def __xenforo_wait_cookies_and_click(driver, timeout):
    cookie_button = expected_conditions.presence_of_element_located(
        (By.XPATH, '//*[@id="qc-cmp2-ui"]/div[2]/div/button[2]/span'))
    WebDriverWait(driver, timeout).until(cookie_button)
    cookie_button = driver.find_element(By.XPATH, '//*[@id="qc-cmp2-ui"]/div[2]/div/button[2]/span')
    cookie_button.click()


def xenforo_login_selenium(login_url='', login_data=None):
    timeout = 100
    driver = webdriver.Firefox()
    s = None
    # selenium.common.exceptions.WebDriverException: Message: Service geckodriver unexpectedly exited. Status code
    # was: 64 miro geckodriver.log geckodriver: error: Found argument '--websocket-port' which wasn't expected,
    # or isn't valid in this context > actualizar geckodriver https://stackoverflow.com/a/70822145/4105601
    try:
        driver.get(login_url)
        __xenforo_wait_cookies_and_click(driver, timeout)
        login_input = driver.find_element(By.NAME, "login")
        login_input.send_keys(login_data.get('vb_login_username', ''))
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys(login_data.get('vb_login_password', ''))
        password_input.send_keys(Keys.RETURN)
        logged_in_username = expected_conditions.presence_of_element_located(
            (By.CLASS_NAME, 'p-navgroup--member'))
        WebDriverWait(driver, timeout).until(logged_in_username)
        s = hijack_cookies(driver)
    except TimeoutException as ex:
        print('Error accessing {}: Timeout: {}'.format(login_url, str(ex)))
    except Exception as ex:
        print('Error accessing {}: Unknown error: {}'.format(login_url, str(ex)))
    finally:
        driver.close()
    return s


regex_thread_id_url = re.compile("/threads/(.+)/")
regex_thread_page_number = re.compile("/page-([0-9]+)")


def update_progress_bar(progress, soup):
    if progress:
        if not progress.total:
            progress.total = int(soup.select_one('ul.pageNav-main>li.pageNav-page:last-child').text)
        progress.update()


def parse_thread_xenforo(session, thread_info, filter_obj: MessageFilter = None, post_processor: MessageProcessor = None,
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
    first_url = thread_info.get("last_page", thread_info['url'])
    if progress and thread_info['last_page']:
        progress.update(n=int(regex_thread_page_number.search(thread_info['last_page']).groups(0)[0]))
    url_parts = urllib.parse.urlparse(first_url)
    base_url = f'{url_parts.scheme}://{url_parts.hostname}'
    current_url = url_parts.path
    while current_url:
        full_url = base_url + current_url
        thread_page = session.get(full_url)
        if not thread_page.ok:
            print(f'Error leyendo {full_url}')
            break
        soup = BeautifulSoup(thread_page.text, features="html.parser")
        update_progress_bar(progress, soup)
        all_messages = soup.find_all("article", {"class": "message"})
        if not thread_info.get('id', None):
            __initialize_thread_info(thread_info, soup)
        for message in all_messages:
            message_id = message.get('data-content').split('-')[-1]
            # skip messages already parsed in previous executions
            if message_id in thread_info["parsed_messages"]:
                continue
            message_as_dict = __parse_message_metadata(message)
            message_tag = message.select_one(
                'div.message-inner>div.message-cell>div.message-main>div.message-content>div.message-userContent'
                '>article.message-body>div.bbWrapper')
            saved_message = message_tag if not post_processor else \
                post_processor.process_message(thread_info=thread_info, post_id=message_id, message=message_tag)
            message_as_dict["message"] = saved_message
            message_as_dict["author"]["is_op"] = message_as_dict["author"]["id"] == thread_info["author_id"]
            print(
                f'#{message_as_dict["index"]} - '
                f'msg_id = {message_id} - author = {message_as_dict["author"]["username"]} - '
                f'{str(message)[:40]}')
            if (not filter_obj) or (filter_obj and (filter_obj.filter_message(message_id, message_as_dict))):
                thread_info["parsed_messages"][message_id] = message_as_dict
                thread_info['last_message'] = message_id

            thread_info['message_count'] = message_as_dict["index"]
            thread_info["last_page"] = full_url
        next_page_link = soup.find('a', {"class": "pageNav-jump--next"})
        if next_page_link:
            current_url = next_page_link.get('href')
        else:
            current_url = ''


def __initialize_thread_info(thread_info, soup):
    thread_info["title"] = soup.select_one('div.p-body-header>div.p-title>h1').text
    thread_info["date"] = soup.select_one('div.p-body-header>div.p-description>ul.listInline>li>a>time').text
    author_info = soup.select_one('div.p-body-header>div.p-description>ul.listInline>li>a.username')
    thread_info["author"] = author_info.text
    thread_info["author_id"] = author_info.get('data-user-id')
    thread_info["id"] = regex_thread_id_url.search(thread_info['url']).groups(0)[-1].split('.')[-1]
    thread_info["hover"] = soup.find('meta', {"property": 'og:description'}).get('content')
    thread_info["first_post_id"] = soup.find_all("article", {"class": "message"})[0].get('id').split('-')[-1]
    thread_info['creation_date'] = thread_info["date"]
    thread_info['modification_date'] = ''
    thread_info['message_count'] = 0
    thread_info["parsed_messages"] = {}


def __parse_message_metadata(message):
    user_name_link = message.select_one(
        'div.message-inner>div.message-cell>section.message-user>div.message-userDetails>h4.message-name>a')
    user_avatar = message.select_one(
        'div.message-inner>div.message-cell>section.message-user>div.message-avatar>div.message-avatar-wrapper>a>img')
    message_link = message.select_one(
        'div.message-inner>div.message-cell>div.message-main>header.message-attribution>ul.message-attribution'
        '-opposite>li:last-child>a')
    message_as_dict = {
        "author": {
            "id": user_name_link.get('data-user-id'),
            "username": user_name_link.text,
            "avatar": user_avatar.get('src') if user_avatar else ''
        },
        "index": int(message_link.text.strip().replace('#', '').replace('.', '')),
        "date": message.select_one(
            'div.message-inner>div.message-cell>div.message-main>header.message-attribution>div.message-attribution'
            '-main>a.u-concealed>time').get(
            'datetime'),
        "link": message_link.get('href'),
        "title": "",
    }
    return message_as_dict
