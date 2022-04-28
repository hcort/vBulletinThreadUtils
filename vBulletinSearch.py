# beautiful soup for HTML parsing
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from vBulletinSession import vbulletin_session


def find_next(soup):
    next_link = soup.find("a", {"rel": "next"})
    return vbulletin_session.config['VBULLETIN']['base_url'] + next_link.get('href', '') if next_link else ''


re_author_from_link = re.compile("member.php\?u=([0-9]+)")
re_thread_id_from_link = re.compile("thread_title_([0-9]+)")


def get_links(base_url, soup, search_query='', strict_search=False):
    links = []
    all_threads_table = soup.select('td[id^="td_threadtitle_"] > div > a[id^="thread_title_"]')
    all_threads_authors = soup.select('td[id^="td_threadtitle_"] > div.smallfont')
    for link in zip(all_threads_table, all_threads_authors):
        thread_id_m = re_thread_id_from_link.search(link[0].attrs.get('id', ''))
        author_id_m = re_author_from_link.search(str(link[1]))
        thread_id = thread_id_m.group(1) if thread_id_m else ''
        if not thread_id and not author_id_m:
            continue
        if (not strict_search) or (strict_search and (link[0].text.lower().find(search_query.lower()) >= 0)):
            links.append(
                {
                    'id': thread_id,
                    'url': base_url + 'showthread.php?t=' + thread_id,
                    'title': link[0].text,
                    'hover': link[0].attrs.get('title', ''),
                    'author': link[1].text.strip(),
                    'author_id': author_id_m.group(1) if author_id_m else ''
                })
    return links


def get_search_id(driver):
    regex_thread_id = re.compile("searchid=([0-9]+)")
    search_id = regex_thread_id.search(driver.current_url)
    return search_id.group(1) if search_id else ''


def loop_search_results(driver, start_url):
    timeout = 100
    current_url = start_url
    first_search = True
    base_url = vbulletin_session.config['VBULLETIN']['base_url']
    search_query = vbulletin_session.config['SEARCHTHREADS'].get('search_words', '')
    strict_search = vbulletin_session.config['SEARCHTHREADS'].get('strict_search', False)
    search_result = {'links': []}
    while current_url:
        if first_search:
            # source = driver.execute_script("return document.body.innerHTML;")
            source = driver.page_source
            search_soup = BeautifulSoup(source, features="html.parser")
            search_result['search_id'] = get_search_id(driver)
            first_search = False
        else:
            driver.get(current_url)
            element_present = EC.presence_of_element_located((By.ID, 'threadslist'))
            WebDriverWait(driver, timeout).until(element_present)
            # source = driver.execute_script("return document.body.innerHTML;")
            source = driver.page_source
            search_soup = BeautifulSoup(source, features="html.parser")
        if search_soup:
            search_result['links'] += get_links(base_url=base_url, soup=search_soup,
                                                search_query=search_query, strict_search=strict_search)
            current_url = find_next(search_soup)
    return search_result


def fill_search_form(driver):
    # TODO read extra parameters from config
    try:
        subforum_select = Select(driver.find_element(By.NAME, "forumchoice[]"))
        subforum_select.select_by_value('23')
        title_only_select = Select(driver.find_element(By.CSS_SELECTOR, "select[name=titleonly]"))
        title_only_select.select_by_value('1')  # 0: search in msg, 1: search in title
        thread_starter_select = Select(driver.find_element(By.CSS_SELECTOR, "select[name=starteronly]"))
        thread_starter_select.select_by_value('1')
    except Exception as err:
        print(str(err))
    minimum_message_field = driver.find_element(By.CSS_SELECTOR, 'div#collapseobj_search_adv table.panel tbody tr '
                                                                 'td:nth-of-type(1) fieldset.fieldset div '
                                                                 'input.bginput')
    minimum_message_field.send_keys('0')
    search_query_input = driver.find_element(By.CSS_SELECTOR, 'td.panelsurround > table.panel > tbody > tr > '
                                                              'td:nth-of-type(1) fieldset.fieldset table tbody tr '
                                                              'td div input.bginput')
    search_query = vbulletin_session.config['SEARCHTHREADS'].get('search_words', '')
    search_query_input.send_keys(search_query)
    thread_author_field = driver.find_element(By.ID, "userfield_txt")
    thread_author = vbulletin_session.config['SEARCHTHREADS'].get('searchuser', '')
    thread_author_field.send_keys(thread_author)
    thread_author_field.send_keys(Keys.RETURN)


def import_cookies_from_session(driver):
    session = vbulletin_session.session
    driver.get(vbulletin_session.config['VBULLETIN']['base_url'])
    for name, value in session.cookies.items():
        driver.delete_cookie(name)
        driver.add_cookie({'name': name, 'value': value})


def click_cookies_button_and_wait(driver):
    try:
        # press accept cookies button so select is not obscured
        element_present = EC.presence_of_element_located((By.CSS_SELECTOR, "button.sd-cmp-JnaLO"))
        WebDriverWait(driver, timeout=1000).until(element_present)
        cookie_button = driver.find_element(By.CSS_SELECTOR, "button.sd-cmp-JnaLO")
        cookie_button.click()
    except Exception as ex:
        print('Cant locate cookies button. ' + str(ex))


def search_selenium():
    # force login here before opening other driver
    base_url = vbulletin_session.config['VBULLETIN']['base_url']
    search_url = base_url + 'search.php?do=process'
    driver = webdriver.Firefox()
    search_result = None
    try:
        import_cookies_from_session(driver)
        driver.get(search_url)
        click_cookies_button_and_wait(driver)
        fill_search_form(driver)
        element_present = EC.presence_of_element_located((By.ID, 'threadslist'))
        WebDriverWait(driver, timeout=1000).until(element_present)
        search_result = loop_search_results(driver, start_url=search_url)
    except TimeoutException as ex:
        print('Error accessing {}: Timeout: {}'.format(search_url, str(ex)))
    except Exception as ex:
        print('Error accessing {}: Timeout: {}'.format(search_url, str(ex)))
    finally:
        driver.close()
    return search_result


def start_searching():
    return search_selenium()
