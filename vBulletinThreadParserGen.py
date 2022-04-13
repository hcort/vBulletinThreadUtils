import calendar
import datetime
import locale

import requests
from bs4 import BeautifulSoup, Tag

from vBulletinSession import vbulletin_session


def find_user_messages_in_thread_list(links, username):
    num_links = len(links)
    for idx, thread_item in enumerate(links):
        print('[' + str(idx) + '/' + str(num_links) + '] - ' + str(thread_item))
        # thread_name = link['title']
        thread_parser = VBulletinThreadParserGEN(thread_item, username)
        author_matches = thread_parser.parse_thread()
        thread_item['matches'] = author_matches


page_nav_bar_selector = 'body > div:nth-child(14) > div:nth-child(1) > div:nth-child(1) > table:nth-of-type(4) ' \
                        '> tr > td:nth-child(2) > div.pagenav > table.tborder > tr '
username_selector = 'tr:nth-child(2) > td.alt2 > div#postmenu_{} > a.bigusername'
user_avatar_selector = 'tr:nth-child(2) > td.alt2 > div.smallfont:nth-of-type(3) > a > img'
user_registration_date_selector = 'tr:nth-child(2) > td.alt2 > div.smallfont:nth-of-type(4) > div:nth-of-type(1)'
user_location_selector = 'tr:nth-child(2) > td.alt2 > div.smallfont:nth-of-type(4) > div:nth-of-type(2)'
user_car_info_selector = 'tr:nth-child(2) > td.alt2 > div.smallfont:nth-of-type(4) > div:nth-of-type(3)'
# post content is in a malformed HTML
#     <td class="alt1" id="td_post_XXX">
#         <div id="post_message_XXX" />
#             message body
#         </div>
# I can't select <div id="post_message_XXX"> because it's empty so I select <td id="td_post_XXX">
post_text_selector = 'tr:nth-of-type(2) > td:nth-of-type(2)'
post_date_selector = 'tr:nth-child(1) > td.thead:nth-child(1)'
post_title_selector = 'tr:nth-child(2) > td.alt1-author > div:nth-of-type(1) > strong'
post_index_selector = 'tr:nth-child(1) > td.thead:nth-child(2) > a'


def get_next_url(soup):
    navigation_menu = soup.select_one(page_nav_bar_selector)
    if navigation_menu:
        next_link = navigation_menu.select_one('a[rel="next"]')
        if next_link:
            return vbulletin_session.config['VBULLETIN']['base_url'] + next_link.get('href', '')
    return ''


def parse_quotes(post_text_start):
    # div > div.smallfont                                     Cita:
    # div > table > tr > td.alt2 > div: nth - child(1)        Cita de...
    # div > table > tr > td.alt2 > div: nth - child(1) > a    Link al perfil
    # div > table > tr > td.alt2 > div: nth - child(2)        Contenido de la cita
    pass


def get_post_text(table):
    post_text_start = table.select_one(post_text_selector)
    # post_text = post_text_start.decode_contents() if post_text_start else ''
    for child in post_text_start.children:
        if type(child) is Tag:
            print(child)
    post_text = post_text_start.prettify(formatter="minimal") if post_text_start else ''
    return post_text


def get_post_date(table):
    date_cell = table.select_one(post_date_selector)
    if not date_cell:
        return ''
    date_time_str = date_cell.text.strip()
    # FIXME locale https://stackoverflow.com/questions/985505/locale-date-formatting-in-python
    if (date_time_str[0] == 'H') or (date_time_str[0] == 'A'):
        locale.setlocale(locale.LC_ALL, 'es_ES')
        today = datetime.datetime.now()
        dia = today.day if date_time_str[0] == 'H' else today.day - 1
        return '{}-{}-{}, {}'.format(dia, calendar.month_name[today.month], today.year, date_time_str.split(',')[1])
    else:
        return date_time_str


def get_post_title(table):
    post_title = table.select_one(post_title_selector)
    return post_title.text if post_title else ''


def get_post_index_and_link(table):
    index_cell = table.select_one(post_index_selector)
    post_index = index_cell.get('name', '') if index_cell else ''
    post_link = index_cell.get('href', '') if index_cell else ''
    return post_index, post_link


def get_user_id_and_name(table, post_id):
    user_name_node = table.select_one(username_selector.format(post_id))
    user_id = user_name_node.get('href', '')[13:] if user_name_node else ''
    user_name = user_name_node.text if user_name_node else ''
    return user_id, user_name


def get_user_avatar(table):
    user_avatar = table.select_one(user_avatar_selector)
    return user_avatar.get('src', '') if user_avatar else ''


class VBulletinThreadParserGEN:

    def __init__(self, thread_item, username_filter=''):
        self.__thread_info = thread_item
        self.__username = username_filter
        self.__first_post_id = ''
        self.__parsed_messages = {}

    def parse_thread(self):
        if not vbulletin_session.session:
            return -1
        current_url = self.__thread_info['url']
        while current_url:
            print('Parsing ' + current_url)
            current_page = vbulletin_session.session.get(current_url)
            if current_page.status_code != requests.codes.ok:
                break
            soup = BeautifulSoup(current_page.text, features="html.parser")
            all_posts_table = soup.select('div[id^="edit"] > table[id^="post"]')
            for table in all_posts_table:
                post_id = self.__parse_post_table(table)
                if not self.__first_post_id:
                    self.__first_post_id = post_id
                    if self.__username == '@OP':
                        self.__username = self.__parsed_messages[self.__first_post_id]['author']['username']
            current_url = get_next_url(soup)
        if self.__first_post_id:
            self.__thread_info['title'] = self.__parsed_messages[self.__first_post_id]['title']
            self.__thread_info['author'] = self.__parsed_messages[self.__first_post_id]['author']['username']
            self.__thread_info['author_id'] = self.__parsed_messages[self.__first_post_id]['author']['id']
        return self.__parsed_messages

    def __parse_post_table(self, table):
        post_id = table.get('id', '')[-9:]
        post_date = get_post_date(table)
        post_index, post_link = get_post_index_and_link(table)
        user_id, user_name = get_user_id_and_name(table, post_id)
        # TODO extra user info, not handled right now
        # user_extra_info = table.select_one('tr:nth-child(2) > td.alt2 > div.smallfont:nth-of-type(2)')
        # user_reg_date = table.select_one(user_registration_date_selector)
        # user_location = table.select_one(user_location_selector)
        # user_car_info = table.select_one(user_car_info_selector)
        # TODO better filtering
        if (not self.__username) or (self.__username == user_name):
            self.__parsed_messages[post_id] = {
                'author': {
                    'id': user_id,
                    'username': user_name,
                    'avatar': get_user_avatar(table),
                },
                'index': post_index,
                'date': post_date,
                'link': post_link,
                'title': get_post_title(table),
                'text': get_post_text(table)
            }
        print('Read post #' + post_index)
        return post_id
