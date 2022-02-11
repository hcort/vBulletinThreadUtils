# beautiful soup for HTML parsing
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup

from vBulletinSession import vbulletin_session


def find_next(soup):
    """
    <div class="pagenav" align="right">
    <table class="tborder" cellspacing="1" cellpadding="3" border="0">
    <tbody>
        <tr>
            <td class="alt1">
                <a  rel="next"
                    class="smallfont"
                    href="showthread.php?t=8142569&amp;page=n"
                    title="Próxima Página - Resultados del xx al xx de xxx">&gt;
                </a>
            </td> <- página siguiente
    """
    pagenav_div = soup.find_all("div", class_="pagenav")
    for div in pagenav_div:
        lista_paginas = div.findChildren("td", class_="alt1", recursive=True)
        for pagina in lista_paginas:
            pag_sig = pagina.find("a", {"rel": "next"})
            if pag_sig:
                next_url = pag_sig.get('href')
                return next_url
    return None


def get_thread_author(cell):
    author = ''
    author_id = ''
    all_span = cell.find_all('span', recursive=True)
    for span in all_span:
        click_event = span.get('onclick', default='')
        if click_event:
            author = span.text
            click_regex = re.compile("member\.php\?u=([0-9]+)")
            m = click_regex.search(click_event)
            if m:
                author_id = m.group(1)
                break
    return [author, author_id]


def get_links(base_url, soup, search_query='', strict_search=False):
    lista_resultados = soup.find('table', {'id': 'threadslist'})
    # <a href="showthread.php?t=8149854"
    #   id="thread_title_8149854">THIS IS THE THREAD TITLE</a>
    regex_id_td = re.compile("td_threadtitle_([0-9]+)")
    # regex_id_link = re.compile("thread_title_([0-9]+)")
    all_table_cells = lista_resultados.find_all('td', {'id': regex_id_td})
    links = []
    for cell in all_table_cells:
        m = regex_id_td.search(cell['id'])
        if m:
            thread_id = m.group(1)
            link = cell.find('a', {'id': 'thread_title_' + thread_id})
            hover = cell.get('title', default='')
            [author, author_id] = get_thread_author(cell)
            nuevo_link = {
                'id': thread_id,
                'url': base_url + 'showthread.php?t=' + thread_id,
                'title': link.text,
                'hover': hover,
                'author': author,
                'author_id': author_id
            }
            if strict_search:
                if nuevo_link['title'].find(search_query) >= 0:
                    links.append(nuevo_link)
            else:
                links.append(nuevo_link)
    return links


def get_token(search_url):
    if not vbulletin_session.session:
        return None
    search_page = vbulletin_session.session.get(search_url)
    if search_page.status_code != requests.codes.ok:
        return
    soup = BeautifulSoup(search_page.text, features="html.parser")
    # <input type="hidden" name="securitytoken" value="1599576018-..." />
    hidden_token = soup.find('input', {'name': 'securitytoken'})
    security_token = hidden_token.get('value', default='')
    return security_token


def build_search_params(search_url, search_query):
    thread_author = vbulletin_session.config['SEARCHTHREADS'].get('searchuser', '')
    security_token = get_token(search_url)
    # search_query = ''
    search_query_encoded = urllib.parse.quote_plus(search_query)
    return {
        's': '',
        'securitytoken': security_token,
        'do': 'process',
        'searchthreadid': '',
        'query': search_query_encoded,
        'titleonly': '1',
        'searchuser': thread_author,
        'starteronly': '0',
        'exactname': '1',
        'replyless': '0',
        # 'replylimit': '1000',  # sólo hilos con más de 1000 respuestas (elimino ruido)
        'searchdate': '0',
        'beforeafter': 'after',
        'sortby': 'lastpost',
        'order': 'descending',
        'showposts': '0',
        'forumchoice[]': '23',  # subforo de empleo
        'childforums': '1',
        'saveprefs': '1'
    }


def start_searching():
    if not vbulletin_session.session:
        return None
    base_url = vbulletin_session.config['VBULLETIN']['base_url']
    search_query = vbulletin_session.config['SEARCHTHREADS'].get('search_words', '')
    strict_search = vbulletin_session.config['SEARCHTHREADS'].get('strict_search', False)
    # otra alternativa:
    # search.php?do=process&query=...&titleonly=...&forumchoice[]=...&
    search_url = base_url + 'search.php'
    # some_forum.com/forum/search.php?do=process
    search_params = build_search_params(search_url, search_query)
    # TODO format this properly
    search_url_process = search_url + '?do=process'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    start_search = vbulletin_session.session.post(search_url_process, data=search_params, headers=headers)
    search_soup = BeautifulSoup(start_search.text, features="html.parser")
    links = get_links(base_url=base_url, soup=search_soup,
                      search_query=search_query, strict_search=strict_search)
    next_results_page = find_next(search_soup)
    while next_results_page:
        next_url = base_url + next_results_page
        next_search = vbulletin_session.session.get(next_url)
        search_soup = BeautifulSoup(next_search.text, features="html.parser")
        links += get_links(base_url=base_url, soup=search_soup,
                           search_query=search_query, strict_search=strict_search)
        next_results_page = find_next(search_soup)
    return links
