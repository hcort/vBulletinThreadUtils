import calendar
import datetime
import locale
import re

import requests
from bs4 import BeautifulSoup
from tqdm.auto import tqdm

import MessageFilter
from html2bbcode import parse_children_in_node
from vBulletinFileUtils import save_parse_result_as_file
from vBulletinSession import vbulletin_session


def find_user_messages_in_thread_list(links, username):
    num_links = len(links)
    for idx, thread_item in enumerate(links):
        print('\n[' + str(idx+1) + '/' + str(num_links) + '] - ' + str(thread_item))
        # thread_name = link['title']
        if username:
            parse_thread(thread_info=thread_item, filter_obj=MessageFilter.MessageFilterByAuthor(username))
        else:
            parse_thread(thread_info=thread_item, filter_obj=None)
        # save results
        if vbulletin_session.config['VBULLETIN'].get('output_format', '') != 'BBCode':
            save_parse_result_as_file(thread_item)


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
    next_link = soup.select_one('a[rel="next"]')
    if next_link:
        return vbulletin_session.config['VBULLETIN']['base_url'] + next_link.get('href', '')


def get_post_HTML(table):
    return table.select_one(post_text_selector)
    # if vbulletin_session.config['VBULLETIN'].get('output_format') == 'BBCode':


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


def parse_post_table(post_id, table):
    post_date = get_post_date(table)
    post_index, post_link = get_post_index_and_link(table)
    user_id, user_name = get_user_id_and_name(table, post_id)
    # TODO extra user info, not handled right now
    # user_extra_info = table.select_one('tr:nth-child(2) > td.alt2 > div.smallfont:nth-of-type(2)')
    # user_reg_date = table.select_one(user_registration_date_selector)
    # user_location = table.select_one(user_location_selector)
    # user_car_info = table.select_one(user_car_info_selector)
    return {
        'author': {
            'id': user_id,
            'username': user_name,
            'is_op': 'tborder-author' in table.attrs.get('class', []),
            'avatar': get_user_avatar(table),
            # TODO add user_extra_info, user_reg_date, user_location, user_car_info
        },
        'index': post_index,
        'date': post_date,
        'link': post_link,
        'title': get_post_title(table),
        'HTML': get_post_HTML(table)
    }


def get_last_page(soup):
    last_or_next_link = soup.select_one('td:nth-last-child(2).alt1 > a')
    if last_or_next_link.text == '>':
        last_or_next_link = soup.select_one('td:nth-last-child(3).alt1 > a')
    regex_id = re.compile("page=([0-9]+)")
    m = regex_id.search(last_or_next_link.attrs.get('href', ''))
    return m.group(1) if m else ''


def update_progress_bar(progress, last_page_found, soup):
    if not last_page_found:
        last_page = get_last_page(soup)
        if last_page:
            progress.total = int(last_page)
    progress.update()
    return True


def update_thread_info(first_post_found, post_id, thread_info, post_dict):
    if not first_post_found:
        thread_info['first_post_id'] = post_id
        thread_info['title'] = post_dict.get('title')
        thread_info['author'] = post_dict.get('author', []).get('username')
        thread_info['author_id'] = post_dict.get('author', []).get('id', [])
    return True


def parse_thread(thread_info: dict, filter_obj: MessageFilter = None):
    if not vbulletin_session.session:
        return -1
    current_url = thread_info.get('url', '')
    thread_info['parsed_messages'] = {}
    if not current_url:
        return
    last_page_found = False
    first_post_found = False
    with tqdm(position=0, leave=True, desc='Parsing ' + current_url) as progress:
        while current_url:
            current_page = vbulletin_session.session.get(current_url)
            if current_page.status_code != requests.codes.ok:
                break
            soup = BeautifulSoup(current_page.text, features="html.parser")
            last_page_found = update_progress_bar(progress, last_page_found, soup)
            all_posts_table = soup.select('div[id^="edit"] > table[id^="post"]')
            for table in all_posts_table:
                post_id = table.get('id', '')[-9:]
                post_dict = parse_post_table(post_id, table)
                if post_dict and ((not filter_obj) or (filter_obj and (filter_obj.filter_message(post_id, post_dict)))):
                    thread_info['parsed_messages'][post_id] = post_dict
                first_post_found = update_thread_info(first_post_found, post_id, thread_info, post_dict)
            current_url = get_next_url(soup)
