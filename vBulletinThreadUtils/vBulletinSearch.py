# beautiful soup for HTML parsing
import json
import os
import re
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from vBulletinThreadUtils.vBulletinLoginSelenium import click_cookies_button, create_driver_and_login
from vBulletinThreadUtils.vBulletinSession import vbulletin_session
from vBulletinThreadUtils.vBulletinThreadParserGen import peek_thread_metadata, normalize_date_string_vbulletin_format


def find_next(soup):
    next_link = soup.find("a", {"rel": "next"})
    return vbulletin_session.base_url + next_link.get('href', '') if next_link else ''


re_author_from_link = re.compile("member.php\?u=(\d+)")
re_thread_id_from_link = re.compile("thread_title_(\d+)")


def get_links(soup, search_query='', strict_search=False):
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


def get_search_id(driver):
    regex_thread_id = re.compile("searchid=(\d+)")
    search_id = regex_thread_id.search(driver.current_url)
    return search_id.group(1) if search_id else ''


def loop_search_results(driver, start_url, search_query, strict_search):
    timeout = 50
    current_url = start_url
    first_search = True
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
            search_result['links'] += get_links(soup=search_soup,
                                                search_query=search_query, strict_search=strict_search)
            current_url = find_next(search_soup)
    return search_result


regex_post_id = re.compile("p=(\d+)")


def search_results_no_parser(driver,
                             search_url,
                             keyword='',
                             author='',
                             time_limit='365',
                             older_than=True,
                             ascending=True,
                             subforum='2'):
    """
    :param driver: the Selenium driver
    :param search_url:
    :param keyword: search keywords
    :param author: search messages by author
    :param time_limit: search option
    :param older_than: search option
    :param ascending: search option
    :param subforum: search option

    :return: A list of messages found

        This method iterates over the search results and extracts the links to the messages without parsing

        See search_selenium and get_links for a search method that parses the results and extracts the messages
        as a dictionary object
    """
    driver.get(search_url)
    has_results = fill_search_form_old_messages_by_author(driver, keyword=keyword, author=author, time_limit=time_limit,
                                                          older_than=older_than,
                                                          ascending=ascending, subforum=subforum)
    if not has_results:
        return
    # element_present = EC.presence_of_element_located((By.ID, 'threadslist'))
    # WebDriverWait(driver, timeout=1000).until(element_present)
    timeout = 50
    current_url = '-'
    messages_found = []
    while current_url:
        try:
            element_present = EC.presence_of_element_located((By.ID, 'threadslist'))
            WebDriverWait(driver, timeout).until(element_present)
            element_present = driver.find_element(By.ID, 'inlinemodform')
            for table in element_present.find_elements_by_xpath(".//table[starts-with(@id, 'post')]"):
                titulo = table.find_element(By.CSS_SELECTOR, 'td.alt1 a').text
                href = table.find_element(By.CSS_SELECTOR, 'div.alt2 a').get_attribute('href')
                post_id_r = regex_post_id.search(href)
                post_id = post_id_r.group(1) if post_id_r else ''
                # print('----------------------------------------------------------------------------------------------')
                # print(titulo)
                # print(table.find_element(By.CLASS_NAME, 'alt2').text[:150])
                # print(href)
                # print('----------------------------------------------------------------------------------------------')
                messages_found.append(href)
            element = driver.find_element(By.LINK_TEXT, '>')
            current_url = element.get_attribute('href')
            driver.get(current_url)
        except Exception as err:
            print(f'Error procesando la lista de mensajes - {str(err)}')
            current_url = None
    return messages_found


def fill_search_form(driver):
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
    minimum_message_field = driver.find_element(By.NAME, 'replylimit')
    minimum_message_field.send_keys(vbulletin_session.minimum_posts)
    search_query_input = driver.find_element(By.CSS_SELECTOR, 'td.panelsurround > table.panel > tbody > tr > '
                                                              'td:nth-of-type(1) fieldset.fieldset table tbody tr '
                                                              'td div input.bginput')
    search_query = vbulletin_session.search_words
    search_query_input.send_keys(search_query)
    thread_author_field = driver.find_element(By.ID, "userfield_txt")
    thread_author = vbulletin_session.search_user
    thread_author_field.send_keys(thread_author)
    thread_author_field.send_keys(Keys.RETURN)


def fill_search_form_old_messages_by_author(driver, keyword='', author='', time_limit='365', older_than=True,
                                            ascending=True, subforum='2'):
    """
    :param driver: the Selenium driver
    :param keyword: search keywords
    :param author: search messages by author
    :param time_limit: search option
    :param older_than: search option
    :param ascending: search option
    :param subforum: search option
    :return:
    """
    thread_list_present = False
    try:
        # subforum_select = Select(driver.find_element(By.NAME, "forumchoice[]"))
        # subforum_select.select_by_value(subforum)
        # title_only_select = Select(driver.find_element(By.CSS_SELECTOR, "select[name=titleonly]"))
        # title_only_select.select_by_value('1')  # 0: search in msg, 1: search in title
        # thread_starter_select = Select(driver.find_element(By.CSS_SELECTOR, "select[name=starteronly]"))
        # thread_starter_select.select_by_value('1')
        # minimum_message_field = driver.find_element(By.CSS_SELECTOR, 'div#collapseobj_search_adv table.panel tbody tr '
        #                                                              'td:nth-of-type(1) fieldset.fieldset div '
        #                                                              'input.bginput')
        # minimum_message_field = driver.find_element(By.NAME, 'replylimit')
        # minimum_message_field.send_keys(vbulletin_session.minimum_posts)

        # actions = ActionChains(driver)
        # actions.move_to_element(element)
        # actions.perform()
        search_by_date_select = Select(driver.find_element(By.NAME, 'searchdate'))
        search_by_date_select.select_by_value(time_limit)
        if older_than:
            older_newer_select = Select(driver.find_element(By.NAME, 'beforeafter'))
            older_newer_select.select_by_value('before')
        if ascending:
            order_messages_select = Select(driver.find_element(By.NAME, 'order'))
            order_messages_select.select_by_value('ascending')
        show_messages_radio = driver.find_element(By.ID, 'rb_showposts_1')
        driver.execute_script("return arguments[0].scrollIntoView();", show_messages_radio)
        show_messages_radio.click()
        search_query_input = driver.find_element(By.CSS_SELECTOR, 'td.panelsurround > table.panel > tbody > tr > '
                                                                  'td:nth-of-type(1) fieldset.fieldset table tbody tr '
                                                                  'td div input.bginput')
        search_query_input.send_keys(keyword)
        thread_author_field = driver.find_element(By.ID, "userfield_txt")
        thread_author_field.send_keys(author)
        thread_author_field.send_keys(Keys.RETURN)
        thread_author_field.send_keys(Keys.RETURN)
        timeout = 20
        element_present = EC.presence_of_element_located((By.ID, 'threadslist'))
        WebDriverWait(driver, timeout).until(element_present)
        thread_list_present = True
    except TimeoutException as err:
        print(f'No se han encontrado resultados - Búsqueda *{keyword}* - *{author}*')
    except Exception as err:
        print(f'Se ha producido un error en la búsqueda: str(err)- Búsqueda *{keyword}* - *{author}*')
    return thread_list_present


def fill_search_form(driver,
                     keyword='', search_in_title=False,
                     author='', threads_started_by_user=False,
                     reply_number='', max_messages=False,
                     time_limit='365', older_than=True,
                     order_type='lastpost', ascending=True,
                     show_as_messages=True,
                     subforum='23'):
    """
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
        # subforum_select = Select(driver.find_element(By.NAME, "forumchoice[]"))
        # subforum_select.select_by_value(subforum)
        # title_only_select = Select(driver.find_element(By.CSS_SELECTOR, "select[name=titleonly]"))
        # title_only_select.select_by_value('1')  # 0: search in msg, 1: search in title
        # thread_starter_select = Select(driver.find_element(By.CSS_SELECTOR, "select[name=starteronly]"))
        # thread_starter_select.select_by_value('1')
        # minimum_message_field = driver.find_element(By.CSS_SELECTOR, 'div#collapseobj_search_adv table.panel tbody tr '
        #                                                              'td:nth-of-type(1) fieldset.fieldset div '
        #                                                              'input.bginput')
        # minimum_message_field = driver.find_element(By.NAME, 'replylimit')
        # minimum_message_field.send_keys(vbulletin_session.minimum_posts)

        # actions = ActionChains(driver)
        # actions.move_to_element(element)
        # actions.perform()

        # keywords
        search_query_input = driver.find_elements(By.NAME, 'query')[2]
        search_query_input.send_keys(keyword)
        if search_in_title:
            search_in_title_select = Select(driver.find_elements(By.NAME, 'titleonly')[1])
            search_in_title_select.select_by_value("1")

        # author
        if author:
            thread_author_field = driver.find_element(By.ID, "userfield_txt")
            thread_author_field.send_keys(author)
        if threads_started_by_user:
            show_as_user_messages_select = Select(driver.find_element(By.NAME, 'starteronly'))
            show_as_user_messages_select.select_by_value("1")

        # number of replies
        if reply_number:
            reply_number_field = driver.find_element(By.NAME, "replylimit")
            reply_number_field.send_keys(reply_number)
        if max_messages:
            reply_number_select = Select(driver.find_element(By.NAME, 'replyless'))
            reply_number_select.select_by_value("1")

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
            driver.execute_script("return arguments[0].scrollIntoView();", show_messages_radio)
            show_messages_radio.click()

        # select subforum
        subforum_select = Select(driver.find_element(By.NAME, "forumchoice[]"))
        subforum_select.select_by_value(subforum)

        search_button = driver.find_element(By.NAME, 'dosearch')
        driver.execute_script("return arguments[0].scrollIntoView();", search_button)
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


def import_cookies_from_session(driver):
    """
        This is the opposite method of vBulletinLoginSelenium.hijack_cookies
    """
    session = vbulletin_session.session
    driver.get(vbulletin_session.base_url)
    for name, value in session.cookies.items():
        driver.delete_cookie(name)
        driver.add_cookie({'name': name, 'value': value})


def search_selenium(search_query, strict_search):
    # force login here before opening other driver
    search_url = vbulletin_session.base_url + 'search.php?do=process'
    os.environ['MOZ_HEADLESS'] = '1'
    driver = webdriver.Firefox()
    search_result = None
    try:
        import_cookies_from_session(driver)
        driver.get(search_url)
        click_cookies_button(driver)
        fill_search_form(driver)
        element_present = EC.presence_of_element_located((By.ID, 'threadslist'))
        WebDriverWait(driver, timeout=1000).until(element_present)
        search_result = loop_search_results(driver,
                                            start_url=search_url,
                                            search_query=search_query,
                                            strict_search=strict_search)
    except TimeoutException as ex:
        print('Error accessing {}: Timeout: {}'.format(search_url, str(ex)))
    except Exception as ex:
        print('Error accessing {}: Timeout: {}'.format(search_url, str(ex)))
    finally:
        driver.close()
    return search_result


def start_searching():
    return search_selenium()


def search_with_posters_metadata():
    """
        search parameters

        keywords
        search in message / search in title

        user name
        user messages / user threads

        message number
        at least / max

        message date
            "searchdate"
                "0"  = Cualquier fecha (opción por defecto)
                "lastvisit" = Tu última visita, "1" = Ayer, "7" = Hace una semana, "14" = Hace 2 Semanas,
                "30" = Hace un mes, "90" = Hace 3 Meses, "180" = Hace 6 Meses, "365" = Hace un año
        older / newer

        order by
            "sortby":
                "rank" = Relevancia, "title" = Título, "replycount" = Número de Respuestas,
                "views" = Número de Visitas, "threadstart" = Fecha Enviado,
                "lastpost" = Fecha de Último Mensaje (opción por defecto), "postusername" = Usuario
        ascending/ descending

        subforum
        recursive

        show as threads / show as messages

        I will use the selenium driver
    """
    driver = vbulletin_session.driver
    search_url = vbulletin_session.base_url + 'search.php?do=process'
    search_query = 'viviendas'
    thread_list = fill_search_form(driver,
                     keyword=search_query, search_in_title=True,
                     author='', threads_started_by_user=False,
                     reply_number='1500', max_messages=False,
                     time_limit='0', older_than=False,
                     order_type='lastpost', ascending=True,
                     show_as_messages=False,
                     subforum='23')
    if thread_list:
        search_result = loop_search_results(driver,
                                            start_url=search_url,
                                            search_query=search_query,
                                            strict_search=False)
        time.sleep(10)
        for res in search_result['links']:
            peek_thread_metadata(res)
            from vBulletinThreadUtils.vBulletinThreadPostersInfo import get_posters_from_thread
            posters = get_posters_from_thread(res['id'])
            time.sleep(10)
            res['posters'] = posters
        with open('./output/posters_file', 'w') as posters_file:
            json.dump(search_result, posters_file)
    driver.close()
    pass


def main():
    search_with_posters_metadata()


if __name__ == "__main__":
    main()
