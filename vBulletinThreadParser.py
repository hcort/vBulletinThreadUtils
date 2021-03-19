import os
import re
from urllib.parse import urlparse
from slugify import slugify

import requests
from bs4 import BeautifulSoup

from vBulletinSearch import find_next


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


def save_image(src_txt, output_dir='', server_root=''):
    img_filename = slugify(src_txt, max_length=250)
    image_path = os.path.join(output_dir, 'imgs', img_filename)
    # server_root is used to build the new img src attribute so a local
    # http server can display them properly
    if server_root:
        rel_path = os.path.relpath(output_dir, server_root)
        image_src_new = os.path.join('\\', rel_path, 'imgs', img_filename)
    else:
        image_src_new = image_path
    if not os.path.exists(image_path):
        with open(image_path, 'wb') as handle:
            try:
                response = requests.get(src_txt, stream=True)
                if not response.ok:
                    print('Error getting image: ' + src_txt)
                for block in response.iter_content(1024):
                    if not block:
                        break
                    handle.write(block)
                return image_src_new
            except ConnectionError as err:
                print('Error getting image: ' + src_txt)
                print(err)
            except Exception as err:
                print('Error getting image: ' + src_txt)
                print(err)
    else:
        return image_src_new
    return src_txt


class VBulletinThreadParser:

    def __init__(self, base_url, thread_name, username, output_dir=''):
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
        self.__thread_filename = ''
        self.__thread_file = None

    def open_file(self, thread_url, output_dir=''):
        regex_id = re.compile("t=([0-9]+)")
        m = regex_id.search(thread_url)
        if m:
            self.__thread_id = m.group(1)
        self.__thread_filename = os.path.join(output_dir, self.__thread_id + '.html')
        if os.path.exists(self.__thread_filename):
            os.remove(self.__thread_filename)
        # 'iso-8859-1', 'cp1252'
        if not self.__thread_file:
            # self.__thread_file = open(self.__thread_filename, "a+", encoding='utf-8')
            self.__thread_file = open(self.__thread_filename, "a+", encoding='latin-1')
        for line in open(os.path.join('resources', "page_header.txt"), "r"):
            if line.startswith('<meta name="description"'):
                self.__thread_file.write(
                    '<meta name=\"description\" content=\"{}\" />'.format(self.__thread_name))
            elif line.startswith('<title>'):
                self.__thread_file.write('<title>' + self.__thread_name + '</title>')
            else:
                self.__thread_file.write(line)

    def close_file(self):
        self.__thread_file.write('\n</body></html>')
        self.__thread_file.close()
        self.__thread_file = None

    def parse_thread(self, session, thread_url, save_images=False, output_dir='', server_root=''):
        current_url = thread_url
        self.__page_number = '1'
        author_matches = 0
        all_post_table_list = []
        while current_url:
            current_page = session.get(current_url)
            if current_page.status_code != requests.codes.ok:
                break
            soup = BeautifulSoup(current_page.text, features="html.parser")
            all_post_table_list += self.parse_thread_posts(soup)
            # busco el enlace a la página siguiente
            next_url = find_next(soup)
            if next_url:
                self.__page_number = get_page_number_from_url(next_url)
                next_url = self.__base_url + next_url
                if next_url != current_url:
                    current_url = next_url
                else:
                    current_url = None
            else:
                current_url = None
        author_matches = len(all_post_table_list)
        self.write_output_file(thread_url, all_post_table_list, save_images=save_images,
                               output_dir=output_dir, server_root=server_root)
        return author_matches

    def parse_post_date_number(self, post_table):
        # thead items contain date and post sequence number
        thead = post_table.find_all('td', class_='thead', recursive=True)
        if len(thead) >= 2:
            self.__current_post_date = thead[0].text.strip()
            self.__current_post_number = thead[1].text.strip()
            # print('Post #' + num_post + '\Fecha: ' + fecha)

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
                                                                                                     self.__base_url)
                if (not self.__username) or (self.__current_post_author == self.__username):
                    self.format_post_url(id_post)
                    self.parse_post_date_number(post_table)
                    content_div = post_table.find('td', {'id': 'td_post_' + id_post})
                    if not content_div:
                        return
                    self.fix_local_links(post_table)
                    post_table_list.append(post_table)
        return post_table_list

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
        forum_url_parts = urlparse(self.__base_url)
        img_regex = forum_url_parts.netloc.replace('www', '//st') + forum_url_parts.path + '[customavatars|images]'
        regex_local_imgs = re.compile(img_regex)
        all_local_imgs = post_table.find_all('img', {'src': regex_local_imgs}, recursive=True)
        for img in all_local_imgs:
            img['src'] = 'https:' + img['src']

    def write_output_file(self, thread_url, all_post_table_list, save_images=False, output_dir='', server_root=''):
        self.open_file(thread_url, output_dir=output_dir)
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
                            img['src'] = save_image(src_txt, output_dir, server_root=server_root)
                            img['src_old'] = src_txt
                table_str += str(child)
            table_str += '</table>'
            self.write_str_to_file(table_str)
        self.close_file()
