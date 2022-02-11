import re

import requests
from bs4 import BeautifulSoup


def remove_quotes(msg):
    citas = msg.find_all('div', text=re.compile('Cita'))
    for cita in citas:
        tabla_sig = cita.find_next('table')
        if tabla_sig.text.find('Cita de') > -1:
            tabla_sig.replaceWith('')
        cita.replaceWith('')


palabras_comunes = ['esa', 'una', 'pero', 'los', 'las', 'que', 'más', 'para', 'así', 'por', 'del', 'con', 'qué', 'tan',
                    'desde', 'como', 'tras', 'pues', 'sus', 'nos']


def check_word(word):
    if len(word) < 3:
        return False
    if word in palabras_comunes:
        return False
    return True


class VBulletinThreadWordCloudParser(object):

    def __init__(self, base_url, username):
        self.__start_url = ''
        self.__page_number = ''
        self.__base_url = base_url
        self.__thread_id = ''
        self.__current_post_url = ''
        self.__current_post_number = ''
        self.__current_post_date = ''
        self.__current_post_author = ''
        self.__current_post_author_profile = ''
        self.__username = username
        self.__resultados = {}
        self.__thread_file = None

    @property
    def resultados(self):
        return self.__resultados

    def find_next(self, soup):
        # Funciona exactamente igual que el de VBulletinSearch
        pagenav_div = soup.find_all("div", class_="pagenav")
        for div in pagenav_div:
            lista_paginas = div.findChildren("td", class_="alt1", recursive=True)
            for pagina in lista_paginas:
                pag_sig = pagina.find("a", {"rel": "next"})
                if pag_sig:
                    next_url = pag_sig.get('href')
                    regex_id = re.compile("page=([0-9]+)")
                    m = regex_id.search(next_url)
                    if m:
                        self.__page_number = m.group(1)
                    return next_url
        return None

    def parse_thread(self, session, thread_url):
        current_url = thread_url
        self.__page_number = '1'
        while current_url:
            current_page = session.get(current_url)
            if current_page.status_code != requests.codes.ok:
                break
            soup = BeautifulSoup(current_page.text, features="html.parser")
            self.parse_thread_posts(soup)
            # busco el enlace a la página siguiente
            next_url = self.find_next(soup)
            if next_url:
                next_url = self.__base_url + next_url
                if next_url != current_url:
                    current_url = next_url
                else:
                    current_url = None
            else:
                current_url = None
        return self.__resultados

    def parse_post_date_number(self, post_table):
        # thead items contain date and post sequence number
        thead = post_table.find_all('td', class_='thead', recursive=True)
        if len(thead) >= 2:
            self.__current_post_date = thead[0].text.strip()
            self.__current_post_number = thead[1].text.strip()

    def parse_post_author(self, post_table, id_post):
        # <a class="bigusername" href="member.php?u=012345">user_name</a>
        try:
            post_menu = post_table.find('div', {'id': 'postmenu_' + id_post})
            user_link = post_menu.find('a', class_='bigusername')
            if user_link:
                self.__current_post_author = user_link.text
                self.__current_post_author_profile = self.__base_url + user_link.get('href')
            else:
                self.__current_post_author = 'Invitado'
                self.__current_post_author_profile = self.__base_url + 'member.php?u=' + post_menu.text
        except Exception as err:
            self.__current_post_author = 'Invitado'
            self.__current_post_author_profile = ''

    def format_post_url(self, id_post):
        self.__current_post_url = '{}showthread.php?t={}&page={}#post{}'.format(self.__base_url,
                                                                                self.__thread_id,
                                                                                self.__page_number,
                                                                                id_post)

    def init_post(self):
        self.__current_post_url = ''
        self.__current_post_number = ''
        self.__current_post_date = ''
        self.__current_post_author = ''
        self.__current_post_author_profile = ''

    def parse_thread_posts(self, soup):
        author_matches = 0
        regex_id = re.compile("edit([0-9]{9})")
        all_posts = soup.find_all('div', id=regex_id, recursive=True)
        for post in all_posts:
            self.init_post()
            m = regex_id.search(post.get('id'))
            if m:
                id_post = m.group(1)
                post_table = post.find('table', {'id': 'post' + id_post})
                if not post_table:
                    return
                self.parse_message(post_table, id_post)

    def parse_message(self, post_table, id_post):
        self.parse_post_author(post_table, id_post)
        if self.__current_post_author == self.__username:
            # no contar palabras en quotes
            msg = post_table.find('td', {'id': 'td_post_' + id_post})
            remove_quotes(msg)
            for linea in msg.contents:
                if linea and (isinstance(linea, str)) and (not linea.startswith('<')) and (len(linea) > 1):
                    # print(linea)
                    linea_limpia = linea.lower().strip()
                    palabras = linea_limpia.split()
                    for palabra in palabras:
                        # FIXME cambiar por expresiones regulares
                        palabra_limpia = "".join(filter(lambda char: char not in "“”«»#$%&()=^[]*+{}¿?.,;:¡!<>/\\\"", palabra))
                        if check_word(palabra_limpia):
                            self.__resultados[palabra_limpia] = self.__resultados.get(palabra_limpia, 0) + 1


def find_user_message_wordcloud(links, username, base_url, session):
    """
        Given a list of threads and a username I parse each thread and build a dictionary with the
        number of times a word is detected in that user messages
    """
    num_links = len(links)
    thread_parser = VBulletinThreadWordCloudParser(base_url, username)
    for idx, link in enumerate(links):
        print('[' + str(idx) + '/' + str(num_links) + '] - ' + str(link))
        thread_name = link['title']
        thread_parser.parse_thread(session, link['url'])
    filtro_pasa_baja = []
    for palabra in thread_parser.resultados:
        if thread_parser.resultados[palabra] < 2:
            filtro_pasa_baja.append(palabra)
    for palabra in filtro_pasa_baja:
        thread_parser.resultados.pop(palabra)
    # print(thread_parser.resultados)
    for w in sorted(thread_parser.resultados, key=thread_parser.resultados.get, reverse=True):
        print(w, thread_parser.resultados[w])
