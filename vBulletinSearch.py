# beautiful soup for HTML parsing
import os
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup


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


class VBulletinSearch:

    def __init__(self, session, base_url):
        self.__session = session
        self.__base_url = base_url

    @property
    def session(self):
        return self.__session

    @property
    def base_url(self):
        return self.__base_url

    def get_token(self, search_url):
        search_page = self.__session.get(search_url)
        if search_page.status_code != requests.codes.ok:
            return
        soup = BeautifulSoup(search_page.text, features="html.parser")
        # <input type="hidden" name="securitytoken" value="1599576018-..." />
        hidden_token = soup.find('input', {'name': 'securitytoken'})
        security_token = hidden_token.get('value', default='')
        return security_token

    def start_searching(self, search_query='', thread_author='', strict_search=False):
        if not self.__session:
            return
        # otra alternativa:
        # search.php?do=process&query=...&titleonly=...&forumchoice[]=...&
        search_url = self.__base_url + 'search.php'
        # self.get_base_url(search_url)
        # some_forum.com/forum/search.php?do=process
        security_token = self.get_token(search_url)
        # search_query = ''
        search_query_encoded = urllib.parse.quote_plus(search_query)
        search_params = {
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
        # TODO format this properly
        search_url_process = search_url + '?do=process'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        start_search = self.__session.post(search_url_process, data=search_params, headers=headers)
        search_soup = BeautifulSoup(start_search.text, features="html.parser")
        links = get_links(base_url=self.__base_url, soup=search_soup,
                          search_query=search_query, strict_search=strict_search)
        next_results_page = find_next(search_soup)
        while next_results_page:
            next_url = self.__base_url + next_results_page
            next_search = self.__session.get(next_url)
            search_soup = BeautifulSoup(next_search.text, features="html.parser")
            links += get_links(base_url=self.__base_url, soup=search_soup,
                               search_query=search_query, strict_search=strict_search)
            next_results_page = find_next(search_soup)
        return links

    def get_base_url(self, search_url):
        path = urllib.parse.urlparse(search_url)
        self.__base_url = path.scheme + '://' + path.netloc + '/'
        path_split = os.path.split(path.path)
        self.__base_url += path_split[0] + '/'
