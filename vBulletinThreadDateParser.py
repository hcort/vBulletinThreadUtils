import datetime
import re

import requests
from bs4 import BeautifulSoup

from vBulletinSession import vbulletin_session


def dia_to_int(dia):
    switcher = {
        'Monday': 1,
        'Tuesday': 2,
        'Wednesday': 3,
        'Thursday': 4,
        'Friday': 5,
        'Saturday': 6,
        'Sunday': 7
    }
    return switcher.get(dia, "Invalid day of week")


def mes_to_int(mes):
    switcher = {
        'ene': 1,
        'feb': 2,
        'mar': 3,
        'abr': 4,
        'may': 5,
        'jun': 6,
        'jul': 7,
        'ago': 8,
        'sep': 9,
        'oct': 10,
        'nov': 11,
        'dic': 12
    }
    return switcher.get(mes, "Invalid day of week")


class VBulletinThreadDateParser(object):

    def __init__(self, base_url, thread_name, username):
        self.__start_url = ''
        self.__page_number = ''
        self.__base_url = base_url
        self.__thread_id = ''
        self.__current_post_url = ''
        self.__current_post_number = ''
        self.__current_post_date = ''
        self.__current_post_author = ''
        self.__current_post_author_profile = ''
        self.__thread_name = thread_name
        self.__username = username
        self.__resultados = [
            [0] * 24,
            [0] * 24,
            [0] * 24,
            [0] * 24,
            [0] * 24,
            [0] * 24,
            [0] * 24
        ]
        self.__thread_file = None

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

    def parse_thread(self, thread_url):
        if not vbulletin_session.session:
            return None
        current_url = thread_url
        self.__page_number = '1'
        while current_url:
            current_page = vbulletin_session.session.get(current_url)
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
                self.parse_post_author(post_table, id_post)
                if self.__current_post_author == self.__username:
                    self.format_post_url(id_post)
                    self.parse_post_date_number(post_table)
                    # convertir fecha a día de la semana
                    # print(self.__current_post_date)
                    # FIXME: hoy, ayer
                    date_comp = self.__current_post_date.split(',')
                    date_str = date_comp[0]
                    hour_str = date_comp[1].strip()
                    if date_str == 'Hoy':
                        today = datetime.datetime.now()
                        dia_semana = today.weekday()
                        pass
                    elif date_str == 'Ayer':
                        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
                        dia_semana = yesterday.weekday()
                        pass
                    else:
                        fecha_comp = date_str.split('-')
                        mes = mes_to_int(fecha_comp[1])
                        dia_semana = datetime.date(int(fecha_comp[2]), mes, int(fecha_comp[0])).weekday()
                    # dia semana empieza con Monday = 0, etc
                    hora_int = int(hour_str[0:2])
                    self.__resultados[dia_semana][hora_int] += 1
                    print('Post #' + self.__current_post_number + '\Fecha: ' + self.__current_post_date)
                    # print(self.__current_post_date + ' = ' + str(dia_semana) + ', ' + str(hora_int))


def find_user_message_timestamp(self, links, username):
    """
        Given a list of threads and a username I parse each thread and build a table with the sum of
        messages from the user for each weekday and each hour

        Ej:
            resultado_total[0][13] = 15
            resultado_total[5][22] = 86

        Means that the user posted 15 messages between 13:00 and 13:59 on mondays and 86 messages
        between 22:00 and 22:59 on fridays

        I use VBulletinThreadDateParser to get the message ditribution for each thread and this method
        only accumulates the results
    """
    num_links = len(links)
    resultado_total = [
        [0] * 24,
        [0] * 24,
        [0] * 24,
        [0] * 24,
        [0] * 24,
        [0] * 24,
        [0] * 24
    ]
    for idx, link in enumerate(links):
        print('[' + str(idx) + '/' + str(num_links) + '] - ' + str(link))
        thread_name = link['title']
        thread_parser = VBulletinThreadDateParser(self.__base_url, thread_name, username)
        resultados = thread_parser.parse_thread(link['url'])
        # añadir resultados locales a horario global
        for idx_dia, dia in enumerate(resultados):
            for idx_hora, hora in enumerate(dia):
                resultado_total[idx_dia][idx_hora] += hora
        print(resultados)
        print(resultado_total)
    # estadística final
    conteo = 0
    for idx_dia, dia in enumerate(resultado_total):
        for idx_hora, hora in enumerate(dia):
            conteo += hora
    print('Total posts: ' + str(conteo))
    for idx_dia, dia in enumerate(resultado_total):
        for idx_hora, hora in enumerate(dia):
            resultado_total[idx_dia][idx_hora] = resultado_total[idx_dia][idx_hora] / conteo
    print(resultado_total)
