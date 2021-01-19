import os
import re

import requests
from bs4 import BeautifulSoup


class VBulletinThreadParser:

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
        self.__thread_file = None

    def open_file(self, thread_url):
        regex_id = re.compile("t=([0-9]+)")
        m = regex_id.search(thread_url)
        if m:
            self.__thread_id = m.group(1)
        filename = os.path.join('output', self.__thread_id + '.html')
        if os.path.exists(filename):
            os.remove(filename)
        # 'iso-8859-1', 'cp1252'
        if not self.__thread_file:
            self.__thread_file = open(filename, "a+", encoding='utf-8')
        for line in open(os.path.join('resources', "page_header.txt"), "r"):
            if line.startswith('<meta name="description"'):
                self.__thread_file.write(
                    '<meta name=\"description\" content=\" {}\" />'.format(self.__thread_name))
            elif line.startswith('<title>' + self.__thread_name + '</title>'):
                self.__thread_file.write('<title>')
            else:
                self.__thread_file.write(line)

    def close_file(self):
        self.__thread_file.write('\n</body></html>')
        self.__thread_file.close()
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

    def parse_thread(self, session, thread_url):
        current_url = thread_url
        self.__page_number = '1'
        author_matches = 0
        self.open_file(thread_url)
        while current_url:
            current_page = session.get(current_url)
            if current_page.status_code != requests.codes.ok:
                break
            soup = BeautifulSoup(current_page.text, features="html.parser")
            author_matches += self.parse_thread_posts(soup)
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
        self.close_file()
        return author_matches

    def parse_post_date_number(self, post_table):
        # thead items contain date and post sequence number
        thead = post_table.find_all('td', class_='thead', recursive=True)
        if len(thead) >= 2:
            self.__current_post_date = thead[0].text.strip()
            self.__current_post_number = thead[1].text.strip()
            # print('Post #' + num_post + '\Fecha: ' + fecha)

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

    def write_str_to_file(self, table_str, retries=10):
        if retries > 0:
            try:
                self.__thread_file.write(table_str)
                return True
            except UnicodeEncodeError as UniErr:
                print(str(UniErr))
                if UniErr.reason == 'surrogates not allowed':
                    # problema con codificación de emojis
                    table_str_2 = table_str.encode('utf-8', errors='surrogatepass')
                    return self.write_str_to_file(str(table_str_2, encoding='utf-8', errors='ignore'), retries - 1)
            except Exception as err:
                print(str(err))
        return False

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
                    content_div = post_table.find('td', {'id': 'td_post_' + id_post})
                    if not content_div:
                        return
                    self.fix_local_links(post_table)
                    # self.fix_youtube_links(post_table)
                    table_str = '<table '
                    for k, v in post_table.attrs.items():
                        if type(v) is list:
                            table_str += k + '=\"' + v[0] + '\" '
                        else:
                            table_str += k + '=\"' + v + '\" '
                    table_str += '>\n'
                    for child in post_table.children:
                        table_str += str(child)
                    table_str += '</table>'
                    if self.write_str_to_file(table_str):
                        author_matches += 1
        return author_matches

    def fix_local_links(self, post_table):
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
            link['href'] = self.__base_url + link['href']
        for link in all_thread_links:
            link['href'] = self.__base_url + link['href']
        # TODO replace some_forum.com using base_url from a config file
        regex_local_imgs = re.compile("//st\.some_forum\.com/forum/customavatars")
        all_local_imgs = post_table.find_all('img', {'src': regex_local_imgs}, recursive=True)
        for img in all_local_imgs:
            img['src'] = 'https:' + img['src']

    # def fix_youtube_links(self, post_table):
    #   """
    #       Elimino esta función porque no necesito insertar a mano este reproductor de vídeos,
    #       basta con corregir el javascript (en page_header.txt) que lo crea
    #   """
    #     """
    #         <div id="24806" align="center">
    #             <div class="video-youtube" align="center">
    #                 <div class="video-container">
    #                     <iframe title="YouTube video player"
    #                         class="youtube-player"
    #                         type="text/html"
    #                         src="//www.youtube.com/embed/sGaX5C7Pm6E"
    #                         allowfullscreen="" width="640" height="390" frameborder="0"/>
    #                 </div>
    #             </div>
    #         </div>
    #     """
    #     javascript_embed_code = post_table.find_all('script', {'language': 'javascript'}, recursive=False)
    #     if not javascript_embed_code:
    #         return
    #     for embed in javascript_embed_code:
    #         for content in embed.contents:
    #             # parse regex: # <!-- # verVideo('6MVGhGdpdDI','4561'); # -->
    #             regex_id = re.compile("verVideo\(\'([^\"&?\\\/]{11}),'([0-9]+)'")
    #             m = regex_id.search(content)
    #             if m:
    #                 id_video = m.group(1)
    #                 id_post = m.group(2)
    #                 outer_div = self.new_soup.new_tag('div', id=id_post, attrs={'align': 'center'})
    #                 middle_div = self.new_soup.new_tag('div', attrs={'align': 'center', 'class': 'video-youtube'})
    #                 inner_div = self.new_soup.new_tag('div', attrs={'class': 'video-container'})
    #                 iframe = self.new_soup.new_tag('iframe', attrs={
    #                     'title': 'YouTube video player',
    #                     'class': 'youtube-player',
    #                     'type': 'text/html',
    #                     'src': 'https://www.youtube.com/embed/' + id_video,
    #                     'allowfullscreen': '',
    #                     'width': '640', 'height': '390', 'frameborder': '0'
    #                 })
    #                 inner_div.insert(iframe)
    #                 middle_div.insert(inner_div)
    #                 outer_div.insert(middle_div)
    #                 embed.parent.insert(outer_div)

