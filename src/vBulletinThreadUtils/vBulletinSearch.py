"""
    Uses the search form in a vBulletin forum filling all the fields

    search_selenium does the search and returns a list with all the search results
"""
import json
import re
import time

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from .vBulletinSession import vbulletin_session
from .vBulletinThreadParserGen import peek_thread_metadata
from .vBulletinThreadPostersInfo import get_posters_from_thread
from .utils import normalize_date_string_vbulletin_format


def _find_next(soup):
    next_link = soup.find('a', {'rel': 'next'})
    return vbulletin_session.base_url + next_link.get('href', '') if next_link else ''


re_author_from_link = re.compile(r'member.php\?u=(\d+)')
re_thread_id_from_link = re.compile(r'thread_title_(\d+)')


def _get_links(soup, search_query='', strict_search=False):
    links = []
    all_threads_table = soup.select('td[id^="td_threadtitle_"] > div > a[id^="thread_title_"]')
    all_threads_authors = soup.select('td[id^="td_threadtitle_"] > div.smallfont')
    all_threads_last_post = soup.select('table#threadslist>tbody>tr>td:nth-of-type(4)>div')
    all_threads_stats = soup.select('table#threadslist>tbody>tr>td:nth-of-type(5)>div>a')
    for link in zip(all_threads_table, all_threads_authors, all_threads_stats, all_threads_last_post):
        thread_id_m = re_thread_id_from_link.search(link[0].attrs.get('id', ''))
        author_id_m = re_author_from_link.search(str(link[1]))
        thread_id = thread_id_m.group(1) if thread_id_m else ''
        if not thread_id and not author_id_m:
            continue
        if (not strict_search) or (strict_search and (link[0].text.lower().find(search_query.lower()) >= 0)):
            links.append(
                {
                    'id': thread_id,
                    'url': vbulletin_session.base_url + 'showthread.php?t=' + thread_id,
                    'title': link[0].text,
                    'hover': link[0].attrs.get('title', ''),
                    'author': link[1].text.strip(),
                    'author_id': author_id_m.group(1) if author_id_m else '',
                    'num_replies': link[2].text,
                    'last_poster': link[3].text.split()[-1],
                    'last_message_url': link[3].select('div>a')[1].get('href', ''),
                    # 'last_message_date': f'{link[3].text.split()[0]} - {link[3].text.split()[1]}'
                    'last_message_date': normalize_date_string_vbulletin_format(
                        link[3].text.split()[0], link[3].text.split()[1])
                })
    return links


def _get_search_id(driver):
    regex_thread_id = re.compile(r'searchid=(\d+)')
    search_id = regex_thread_id.search(driver.current_url)
    return search_id.group(1) if search_id else ''


def _loop_search_results(driver, start_url, search_query, strict_search):
    timeout = 50
    current_url = start_url
    first_search = True
    search_result = {'links': []}
    while current_url:
        if first_search:
            source = driver.page_source
            search_soup = BeautifulSoup(source, features='html.parser')
            search_result['search_id'] = _get_search_id(driver)
            first_search = False
        else:
            driver.get(current_url)
            element_present = EC.presence_of_element_located((By.ID, 'threadslist'))
            WebDriverWait(driver, timeout).until(element_present)
            source = driver.page_source
            search_soup = BeautifulSoup(source, features='html.parser')
        if search_soup:
            search_result['links'] += _get_links(soup=search_soup,
                                                 search_query=search_query, strict_search=strict_search)
            current_url = _find_next(search_soup)
    return search_result


def _fill_search_form_all_parameters(driver,
                                     keyword: str = '',
                                     search_in_title: bool = False,
                                     author: str = '', threads_started_by_user: bool = False,
                                     reply_number: str = '', max_messages: bool = False,
                                     time_limit: str = '365', older_than: bool = True,
                                     order_type: str = 'lastpost', ascending: bool = True,
                                     show_as_messages: bool = True,
                                     subforum: str = '23') -> bool:
    """
    :param max_messages:
    :param reply_number:
    :param threads_started_by_user:
    :param search_in_title:
    :param order_type:
    :param show_as_messages:
    :param driver: the Selenium driver
    :param search_url:
    :param keyword: search keywords
    :param author: search messages by author
    :param time_limit: search option
    :param older_than: search option
    :param ascending: search option
    :param subforum: search option
    :return:
    """
    thread_list_present = False
    search_url = vbulletin_session.base_url + 'search.php'
    driver.get(search_url)
    try:
        # keywords
        search_query_input = driver.find_elements(By.NAME, 'query')[2]
        search_query_input.send_keys(keyword)
        if search_in_title:
            search_in_title_select = Select(driver.find_elements(By.NAME, 'titleonly')[1])
            search_in_title_select.select_by_value('1')

        # author
        if author:
            thread_author_field = driver.find_element(By.ID, 'userfield_txt')
            thread_author_field.send_keys(author)
        if threads_started_by_user:
            show_as_user_messages_select = Select(driver.find_element(By.NAME, 'starteronly'))
            show_as_user_messages_select.select_by_value('1')

        # number of replies
        if reply_number:
            reply_number_field = driver.find_element(By.NAME, 'replylimit')
            reply_number_field.send_keys(reply_number)
        if max_messages:
            reply_number_select = Select(driver.find_element(By.NAME, 'replyless'))
            reply_number_select.select_by_value('1')

        # date
        search_by_date_select = Select(driver.find_element(By.NAME, 'searchdate'))
        search_by_date_select.select_by_value(time_limit)
        if older_than:
            older_newer_select = Select(driver.find_element(By.NAME, 'beforeafter'))
            older_newer_select.select_by_value('before')

        # order messages
        if order_type:
            order_by_select = Select(driver.find_element(By.NAME, 'sortby'))
            order_by_select.select_by_value(order_type)
        if ascending:
            order_messages_select = Select(driver.find_element(By.NAME, 'order'))
            order_messages_select.select_by_value('ascending')

        if show_as_messages:
            # show as threads is the default value of this radio
            show_messages_radio = driver.find_element(By.ID, 'rb_showposts_1')
            driver.execute_script('return arguments[0].scrollIntoView();', show_messages_radio)
            show_messages_radio.click()

        # select subforum
        subforum_select = Select(driver.find_element(By.NAME, 'forumchoice[]'))
        subforum_select.select_by_value(subforum)

        search_button = driver.find_element(By.NAME, 'dosearch')
        driver.execute_script('return arguments[0].scrollIntoView();', search_button)
        search_button.click()

        timeout = 20
        element_present = EC.presence_of_element_located((By.ID, 'threadslist'))
        WebDriverWait(driver, timeout).until(element_present)
        thread_list_present = True
    except TimeoutException as err:
        print(f'No se han encontrado resultados {err} - Búsqueda *{keyword}* - *{author}*')
    except Exception as err:
        print(f'Se ha producido un error en la búsqueda: {err} - Búsqueda *{keyword}* - *{author}*')
    return thread_list_present


def _import_cookies_from_session(driver):
    """
        This is the opposite method of vBulletinLoginSelenium.hijack_cookies
    """
    session = vbulletin_session.session
    driver.get(vbulletin_session.base_url)
    for name, value in session.cookies.items():
        driver.delete_cookie(name)
        driver.add_cookie({'name': name, 'value': value})


def search_selenium(driver=None,
                    search_query: str = '',
                    strict_search: bool = False,
                    search_in_title: bool = False,
                    author: str = '', threads_started_by_user: bool = False,
                    reply_number: str = '', max_messages: bool = False,
                    time_limit: str = '365', older_than: bool = True,
                    order_type: str = 'lastpost', ascending: bool = True,
                    show_as_messages: bool = True,
                    subforum: str = '23') -> list:
    # force login here before opening other driver
    search_url = vbulletin_session.base_url + 'search.php?do=process'
    # os.environ['MOZ_HEADLESS'] = '1'
    # driver = webdriver.Firefox()
    search_result = None
    try:
        # _import_cookies_from_session(driver)
        driver.get(search_url)
        # click_cookies_button(driver)
        if _fill_search_form_all_parameters(driver,
                                            keyword=search_query, search_in_title=search_in_title,
                                            author=author, threads_started_by_user=threads_started_by_user,
                                            reply_number=reply_number, max_messages=max_messages,
                                            time_limit=time_limit, older_than=older_than,
                                            order_type=order_type, ascending=ascending,
                                            show_as_messages=show_as_messages,
                                            subforum=subforum):
            search_result = _loop_search_results(driver,
                                                 start_url=search_url,
                                                 search_query=search_query,
                                                 strict_search=strict_search)
    except TimeoutException as ex:
        print(f'Error accessing {search_url}: Timeout: {str(ex)}')
    except Exception as ex:
        print(f'Error accessing {search_url}: Timeout: {str(ex)}')
    finally:
        driver.close()
    return search_result


def search_with_posters_metadata(driver=None,
                                 search_query: str = '',
                                 strict_search: bool = False,
                                 search_in_title: bool = False,
                                 author: str = '', threads_started_by_user: bool = False,
                                 reply_number: str = '', max_messages: bool = False,
                                 time_limit: str = '365', older_than: bool = True,
                                 order_type: str = 'lastpost', ascending: bool = True,
                                 show_as_messages: bool = True,
                                 subforum: str = '23'):
    """
        see _fill_search_form_all_parameters for the description of parameters
    """
    if not driver:
        driver = vbulletin_session.driver
    search_result = search_selenium(driver=driver,
                                    strict_search=strict_search,
                                    search_query=search_query, search_in_title=search_in_title,
                                    author=author, threads_started_by_user=threads_started_by_user,
                                    reply_number=reply_number, max_messages=max_messages,
                                    time_limit=time_limit, older_than=older_than,
                                    order_type=order_type, ascending=ascending,
                                    show_as_messages=show_as_messages,
                                    subforum=subforum)
    for res in search_result['links']:
        peek_thread_metadata(res)
        posters = get_posters_from_thread(res['id'])
        time.sleep(10)
        res['posters'] = posters
    with open('./output/posters_file', 'w', encoding='utf-8') as posters_file:
        json.dump(search_result, posters_file)
    pass


def main():
    search_with_posters_metadata()


if __name__ == '__main__':
    main()
