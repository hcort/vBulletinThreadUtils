import os
import re
from urllib.parse import urlparse
from slugify import slugify

import requests
from bs4 import BeautifulSoup

from vBulletinFileUtils import save_image, open_thread_file, write_str_to_thread_file, close_thread_file
from vBulletinSearch import find_next
from vBulletinSession import vbulletin_session


def find_user_messages_in_thread_list(links, username):
    num_links = len(links)
    for idx, link in enumerate(links):
        print('[' + str(idx) + '/' + str(num_links) + '] - ' + str(link))
        thread_name = link['title']
        thread_parser = VBulletinThreadParser(thread_name, username)
        author_matches = thread_parser.parse_thread(link['url'])
        link['matches'] = author_matches


def get_page_number_from_url(next_url):
    regex_id = re.compile("page=([0-9]+)")
    m = regex_id.search(next_url)
    if m:
        return m.group(1)
    return -1


def parse_post_author(post_table, id_post, base_url):
    # <a class="bigusername" href="member.php?u=012345">user_name</a>
    try:
        post_menu = post_table.find('div', {'id': 'postmenu_' + id_post})
        user_link = post_menu.find('a', class_='bigusername')
        if user_link:
            post_author = user_link.text
            post_author_profile = base_url + user_link.get('href')
        else:
            post_author = 'Invitado'
            post_author_profile = base_url + 'member.php?u=' + post_menu.text
    except Exception:
        post_author = 'Invitado'
        post_author_profile = ''
    return [post_author, post_author_profile]


def fix_local_links(post_table):
    """
        Links locales:
        - citas de otros mensajes:
            <a href="showthread.php?t=...&page=..#post..."  ...> </a>
        - número de mensaje en el hilo:
            <a href="showthread.php?p=...#post..." ...></a>
        - enlace al perfil del usuario
            <a class="bigusername" href="member.php?u=...">...</a>
        Imágenes
            <img id="fcterremoto" class="avatar" src="//st.some_forum.com/forum/customavatars/....gif"
                alt="Avatar de ..." title="Avatar de ..." width="120" height="120" border="0">
    """
    regex_member = re.compile("member\.php\?u=([0-9]+)")
    regex_thread = re.compile("showthread\.php\?[pt]=([0-9]+)")
    all_member_links = post_table.find_all('a', {'href': regex_member}, recursive=True)
    all_thread_links = post_table.find_all('a', {'href': regex_thread}, recursive=True)
    for link in all_member_links:
        link['href'] = vbulletin_session.config['VBULLETIN']['base_url'] + link['href']
    for link in all_thread_links:
        link['href'] = vbulletin_session.config['VBULLETIN']['base_url'] + link['href']
    forum_url_parts = urlparse(vbulletin_session.config['VBULLETIN']['base_url'])
    img_regex = forum_url_parts.netloc.replace('www', '//st') + forum_url_parts.path + '[customavatars|images]'
    regex_local_imgs = re.compile(img_regex)
    all_local_imgs = post_table.find_all('img', {'src': regex_local_imgs}, recursive=True)
    for img in all_local_imgs:
        img['src'] = 'https:' + img['src']


class VBulletinThreadParser:

    def __init__(self, thread_name, username):
        self.__start_url = ''
        self.__page_number = ''
        self.__thread_id = ''
        self.__current_post_url = ''
        self.__current_post_number = ''
        self.__current_post_date = ''
        self.__current_post_author = ''
        self.__current_post_author_profile = ''
        self.__thread_name = thread_name
        self.__username = username

    def parse_thread(self, thread_url):
        if not vbulletin_session.session:
            return -1
        current_url = thread_url
        self.__page_number = '1'
        author_matches = 0
        all_post_table_list = []
        while current_url:
            current_page = vbulletin_session.session.get(current_url)
            if current_page.status_code != requests.codes.ok:
                break
            soup = BeautifulSoup(current_page.text, features="html.parser")
            all_post_table_list += self.parse_thread_posts(soup)
            # busco el enlace a la página siguiente
            next_url = find_next(soup)
            if next_url:
                self.__page_number = get_page_number_from_url(next_url)
                next_url = vbulletin_session.config['VBULLETIN']['base_url'] + next_url
                if next_url != current_url:
                    current_url = next_url
                else:
                    current_url = None
            else:
                current_url = None
        author_matches = len(all_post_table_list)
        self.write_output_file(thread_url, all_post_table_list)
        return author_matches

    def parse_post_date_number(self, post_table):
        # thead items contain date and post sequence number
        thead = post_table.find_all('td', class_='thead', recursive=True)
        if len(thead) >= 2:
            self.__current_post_date = thead[0].text.strip()
            self.__current_post_number = thead[1].text.strip()
            # print('Post #' + num_post + '\Fecha: ' + fecha)

    def format_post_url(self, id_post):
        self.__current_post_url = '{}showthread.php?t={}&page={}#post{}'.format(
            vbulletin_session.config['VBULLETIN']['base_url'],
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
        post_table_list = []
        for post in all_posts:
            self.init_post()
            m = regex_id.search(post.get('id'))
            if m:
                id_post = m.group(1)
                post_table = post.find('table', {'id': 'post' + id_post})
                if not post_table:
                    return
                [self.__current_post_author, self.__current_post_author_profile] = parse_post_author(post_table,
                                                                                                     id_post,
                                                                                                     vbulletin_session.config[
                                                                                                         'VBULLETIN'][
                                                                                                         'base_url'])
                if (not self.__username) or (self.__current_post_author == self.__username):
                    self.format_post_url(id_post)
                    self.parse_post_date_number(post_table)
                    content_div = post_table.find('td', {'id': 'td_post_' + id_post})
                    if not content_div:
                        return
                    fix_local_links(post_table)
                    post_table_list.append(post_table)
        return post_table_list

    def write_output_file(self, thread_url, all_post_table_list):
        save_images = (vbulletin_session.config['VBULLETIN'].get('save_images', '') == 'True')
        regex_id = re.compile("t=([0-9]+)")
        m = regex_id.search(thread_url)
        if m:
            self.__thread_id = m.group(1)
        thread_file = open_thread_file(thread_url, self.__thread_id, self.__thread_name)
        for post_table in all_post_table_list:
            table_str = '<table '
            for k, v in post_table.attrs.items():
                if type(v) is list:
                    table_str += k + '=\"' + v[0] + '\" '
                else:
                    table_str += k + '=\"' + v + '\" '
            table_str += '>\n'
            for child in post_table.children:
                if save_images:
                    all_imgs = post_table.find_all('img', recursive=True)
                    for img in all_imgs:
                        src_txt = img['src']
                        if not img.get('src_old', None):
                            # some nodes are parsed more than once (!) hack to detect this
                            img['src'] = save_image(src_txt)
                            img['src_old'] = src_txt
                table_str += str(child)
            table_str += '</table>'
            write_str_to_thread_file(thread_file, table_str)
        close_thread_file(thread_file)
