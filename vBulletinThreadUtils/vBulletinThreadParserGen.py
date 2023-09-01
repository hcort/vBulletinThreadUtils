import calendar
import datetime
from datetime import datetime, timedelta
import locale
import re

import requests
from bs4 import BeautifulSoup

from vBulletinThreadUtils import MessageFilter, MessageProcessor
from vBulletinThreadUtils.ProgressVisor import ProgressVisor
from vBulletinThreadUtils.vBulletinFileUtils import save_parse_result_as_file
from vBulletinThreadUtils.vBulletinSession import vbulletin_session


def thread_id_to_thread_link_dict(thread_id):
    """
    Builds an empty thread_info dictionary with just thread_id and url values

    :param thread_id:
    :return: a thread_info dictionary in a format expected by the parse_thread method
    """
    return {
        'id': thread_id,
        'url': '{base}/showthread.php?t={thread_id}'.format(
            base=vbulletin_session.base_url, thread_id=thread_id),
        'title': '',
        'hover': '',
        'author': '',
        'author_id': ''
    }


regex_message_id_number = re.compile("postmenu_([0-9]+)")


def peek_thread_metadata(thread_info: dict):
    """

    :param thread_info:
    :return: basic info about the thread, it does not parse any messages

    Fields of thread_info filled:

        thread_info['creation_date']
        thread_info['modification_date']
        thread_info['message_count']

        thread_info['author']
        thread_info['author_id']
        thread_info['first_post_id']

    """
    thread_info['parsed_messages'] = {}
    if not vbulletin_session.session or not thread_info.get('url', ''):
        return None
    current_page = vbulletin_session.session.get(thread_info['url'])
    if current_page.status_code != requests.codes.ok:
        print('Error getting {} - response code: {}'.format(thread_info['url'], current_page.status_code))
        return
    soup = BeautifulSoup(current_page.text, features="html.parser")
    thread_info['title'] = soup.select_one('title').text
    __update_thread_timestamps(thread_info=thread_info, soup=soup)

    op_info = soup.select_one('div[id^="postmenu_"]')
    if op_info:
        thread_info['first_post_id'] = op_info.get('id').split('_')[-1]
        if op_info.select_one('a'):
            thread_info['author'] = op_info.select_one('a').get('href').split('=')[-1]
            thread_info['author_id'] = op_info.select_one('a').text
        else:
            thread_info['author_id'] = op_info.text.strip()


def parse_thread(thread_info: dict, filter_obj: MessageFilter = None, post_processor: MessageProcessor = None,
                 progress: ProgressVisor = None):
    """
    Main method to parse a forum thread
    :param progress: Used to show a progress bar if desired. See ProgressVisor
    :param thread_info is a dictionary that must contain a field called url
    with the URL of the starting point of the parser
    :param filter_obj: see MessageFilter.py
    :param post_processor: see MessageProcessor.py
    :return: there is no return value. Parsed data is stored in new keys inside thread_info

    thread_info
    {
        'id': #####
        'url': #####
    }

    thread_info['url'] is built using the base_url paremeter in config.ini
    See thread_id_to_thread_link_dict in search.py

    After parsing a thread all the relevant data is stored into thread_info
    thread_info
    {
        'id': #####
        'url': #####
        'title': title of the thread
        'first_post_id': the id of the first post of the thread
        'author': username of the thread author
        'author_id': id of the thread author
        'last_page': number of the last parsed page (1)
        'last_message':  number of the last parsed message (2)
        'parsed_messages': a dictionary of parsed messages.
                    keys are the ids of the messages
                    values are dictionaries of the format described below
    }

    (1) last_page can be used to skip the thread pages that were already parsed, as it will
            generate a starting point url pointing to that last_page
            - basic URL = {base_url}/showthread.php?t={thread_id}
            - paged URL = {base_url}/showthread.php?t={thread_id}&page={last_page}
        last_page WILL BE UPDATED with the last parsed page in this execution

    (2) last_message is used to avoid storing already parsed messages, but all the message from
            the starting point to last_message will be parsed
        last_message WILL BE UPDATED with the last parsed message in this execution

    Example:
        last_page = 3; last_message = 60
        typical vbulletin page has 25 messages so page number #3 will start with post #51
        The parser will NOT parse pages #1 and #2. It will start with page #3.
        The parser will parse messages #51, #52, ..., #59 and #60 but it won't store them in the output. The
            first message in parsed_messages will be #61

    Each of these parsed messages has the following format:
    {
        'author': {
            'id': ...,
            'username': ...,
            'is_op': True/False,
            'avatar': avatar url
        },
        'index': sequential number of post inside thread,
        'date': ...,
        'link': url to this post,
        'title': ,
        'HTML': a BeautifulSoup objects that represents the HTML code of a
                post message
    }

    """
    thread_info['parsed_messages'] = {}
    current_url = thread_info.get('url', '')
    if thread_info.get('last_page', ''):
        current_url = f'{current_url}&page={thread_info["last_page"]}'
    if not vbulletin_session.session or not current_url:
        return None

    if progress and thread_info.get('last_page', None):
        progress.update(n=thread_info["last_page"])
    while current_url:
        current_page = vbulletin_session.session.get(current_url)
        if current_page.status_code != requests.codes.ok:
            print('Error getting {} - response code: {}'.format(current_url, current_page.status_code))
            break
        soup = BeautifulSoup(current_page.text, features="html.parser")
        __update_progress_bar(progress, soup)
        __search_and_parse_messages(thread_info, soup, filter_obj, current_url, post_processor)
        thread_info["last_page"] = __get_page_number_from_url(current_url)
        current_url = __get_next_url(soup)


def find_user_messages_in_thread_list(links, username, thread_index_file=''):
    num_links = len(links)
    for idx, thread_item in enumerate(links):
        try:
            print('\n[' + str(idx + 1) + '/' + str(num_links) + '] - ' + str(thread_item))
            # thread_name = link['title']
            if username:
                parse_thread(thread_info=thread_item, filter_obj=MessageFilter.MessageFilterByAuthor(username))
            else:
                parse_thread(thread_info=thread_item, filter_obj=None)
            # save results
            if vbulletin_session.config['VBULLETIN'].get('output_format', '') != 'BBCode':
                save_parse_result_as_file(thread_item, save_to_index=True, thread_index_file=thread_index_file)
            thread_item['parsed_messages'] = {}
        except Exception as ex:
            print('Error handling {}: {}'.format(thread_item['url'], str(ex)))
            vbulletin_session.session_restart()


page_nav_bar_selector = 'body > div:nth-child(14) > div:nth-child(1) > div:nth-child(1) > table:nth-of-type(4) ' \
                        '> tr > td:nth-child(2) > div.pagenav > table.tborder > tr '
username_selector = 'tr:nth-child(2) > td.alt2 > div#postmenu_{} > a.bigusername'
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

regex_page_number = re.compile("page=([0-9]+)")


def normalize_date_string(date_string):
    """

    :param date_string: format = '2017-07-21T16:17:16+00:00'
    :return: format = aaaa-mm-dd - hh:mm with hours and minutes corrected from UTC
    """
    parsed_time = datetime.strptime(date_string[:-6], '%Y-%m-%dT%H:%M:%S')
    from time import altzone
    diff_hour = altzone / 3600
    offset_time = parsed_time - timedelta(hours=diff_hour)
    return offset_time.strftime('%Y-%m-%d - %H:%M')


month_replacement_number = {'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'may': '05', 'jun': '06',
                            'jul': '07', 'ago': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'}


def normalize_date_string_vbulletin_format(vbulletin_date, hour_minutes):
    """

    :param hour_minutes: format = 'hh:mm'
    :param vbulletin_date: 'dd-mmm-aaaa' / 'Hoy' / 'Ayer'
        mmm are months in spanish
    :return: format = aaaa-mm-dd - hh:mm
    """
    from datetime import date, timedelta
    if vbulletin_date[0] == 'H':
        return f"{date.today().strftime('%Y-%m-%d')} - {hour_minutes}"
    elif vbulletin_date[0] == 'A':
        yesterday = date.today() - timedelta(days=1)
        return f"{yesterday.strftime('%Y-%m-%d')} - {hour_minutes}"
    else:
        month_num = month_replacement_number[vbulletin_date[3:6]]
        return datetime.strptime(
            f"{vbulletin_date.replace(vbulletin_date[3:6], month_num)} - {hour_minutes}", '%d-%m-%Y - %H:%M'
        ).strftime('%Y-%m-%d - %H:%M')


def __update_thread_timestamps(thread_info, soup):
    if thread_info.get('creation_date', ''):
        return
    all_script_data = soup.find_all('script', {'type': 'application/ld+json'})
    json_type_str = '"@type":"DiscussionForumPosting"'
    for data in all_script_data:
        type_pos = data.text.find(json_type_str, 30, 90)
        if type_pos >= 0:
            first_message_time = normalize_date_string_vbulletin_format(
                soup.select_one('table[id^="post"] > tr > td.thead').text.split(',')[0].strip(),
                soup.select_one('table[id^="post"] > tr > td.thead').text.split(',')[-1].strip()
            )
            regex_date_published = re.compile('datePublished":\s*"([\d\-T\+:]{25})').search(data.text)
            regex_date_modified = re.compile('dateModified":\s*"([\d\-T\+:]{25})').search(data.text)
            regex_interaction_count = re.compile('userInteractionCount":\s*"(\d+)"').search(data.text)
            thread_info['creation_date'] = normalize_date_string(
                regex_date_published.group(1)) if regex_date_published else ''
            thread_info['modification_date'] = normalize_date_string(
                regex_date_modified.group(1)) if regex_date_modified else ''
            thread_info['message_count'] = int(regex_interaction_count.group(1)) + 1 if regex_interaction_count else 0
            if first_message_time != thread_info['creation_date']:
                print(
                    f"{thread_info['id']}: {first_message_time} - {thread_info['creation_date']} - {thread_info['modification_date']}")
                delta_hour = datetime.datetime.strptime(first_message_time, '%d-%m-%Y - %H:%M') - \
                             datetime.datetime.strptime(thread_info['creation_date'], '%d-%m-%Y - %H:%M')
                thread_info['creation_date'] = first_message_time
                thread_info['modification_date'] = \
                    datetime.datetime.strptime(thread_info['modification_date'], '%d-%m-%Y - %H:%M') + delta_hour
                print(
                    f"{thread_info['id']}: {first_message_time} - {thread_info['creation_date']} - {thread_info['modification_date']}")
            return


def __search_and_parse_messages(thread_info, soup, filter_obj, current_url, post_processor):
    all_posts_table = soup.select('div[id^="edit"] > table[id^="post"]')
    if not all_posts_table:
        print('Error in thread {} - No messages found'.format(current_url))
        return
    for table in all_posts_table:
        post_id = table.get('id', '')[-9:]
        if post_id in thread_info['parsed_messages']:
            continue
        post_dict = __parse_post_metadata(thread_info, post_id, table)
        # I want to have the message metadata in the dictionary before calling the post-processor
        thread_info['parsed_messages'][post_id] = post_dict

        saved_message = table.select_one(post_text_selector) if not post_processor else \
            post_processor.process_message(thread_info=thread_info, post_id=post_id,
                                           message=table.select_one(post_text_selector))
        thread_info['parsed_messages'][post_id]['message'] = saved_message

        if post_dict and ((not filter_obj) or (filter_obj and (filter_obj.filter_message(post_id, post_dict)))):
            thread_info['last_message'] = post_dict.get('index', 0)
        else:
            thread_info['parsed_messages'].pop(post_id)
        __update_thread_info(post_id, thread_info, post_dict)
        __update_thread_timestamps(thread_info, soup)


def __get_next_url(soup):
    next_link = soup.select_one('a[rel="next"]')
    return f"{vbulletin_session.base_url}{next_link.get('href', '')}" if next_link else ''


def __get_post_date(table):
    date_cell = table.select_one(post_date_selector)
    if not date_cell:
        return ''
    date_time_str = date_cell.text.strip()
    # FIXME locale https://stackoverflow.com/questions/985505/locale-date-formatting-in-python
    if (date_time_str[0] == 'H') or (date_time_str[0] == 'A'):
        locale.setlocale(locale.LC_ALL, 'es_ES')
        today = datetime.now()
        dia = today.day if date_time_str[0] == 'H' else today.day - 1
        # return '{}-{}-{}, {}'.format(dia, calendar.month_name[today.month], today.year, date_time_str.split(',')[1])
        return f"{today.year}-{today.month}-{today.day} - {date_time_str.split(',')[1]}"
    else:
        return date_time_str


def __get_post_title(table):
    post_title = table.select_one(post_title_selector)
    return post_title.text if post_title else ''


def __get_post_index_and_link(table):
    index_cell = table.select_one(post_index_selector)
    post_index = index_cell.get('name', '') if index_cell else ''
    post_link = index_cell.get('href', '') if index_cell else ''
    return post_index, post_link


def __get_user_id_and_name(table, post_id):
    user_name_node = table.select_one(username_selector.format(post_id))
    user_id = user_name_node.get('href', '')[13:] if user_name_node else ''
    user_name = user_name_node.text if user_name_node else ''
    return user_id, user_name


def __get_user_avatar(table):
    user_avatar = table.select_one('img#fcterremoto')
    return user_avatar.get('src', '') if user_avatar else ''


def __parse_post_metadata(thread_info, post_id, table):
    post_date = __get_post_date(table)
    post_index, post_link = __get_post_index_and_link(table)
    user_id, user_name = __get_user_id_and_name(table, post_id)
    # TODO extra user info, not handled right now
    # user_extra_info = table.select_one('tr:nth-child(2) > td.alt2 > div.smallfont:nth-of-type(2)')
    # user_reg_date = table.select_one(user_registration_date_selector)
    # user_location = table.select_one(user_location_selector)
    return {
        'author': {
            'id': user_id,
            'username': user_name,
            'is_op': 'tborder-author' in table.attrs.get('class', []),
            'avatar': __get_user_avatar(table),
        },
        'index': post_index,
        'date': post_date,
        'link': post_link,
        'title': __get_post_title(table),
        'message': None
    }


def __get_page_number_from_url(url):
    m = regex_page_number.search(url)
    return m.group(1) if m else ''


def __get_last_page(soup):
    last_or_next_link = soup.select_one('td:nth-last-child(2).alt1 > a')
    if not last_or_next_link:
        return ''
    if last_or_next_link.text == '>':
        last_or_next_link = soup.select_one('td:nth-last-child(3).alt1 > a')
    return __get_page_number_from_url(last_or_next_link.attrs.get('href', ''))


def __update_progress_bar(progress, soup):
    if not progress:
        return
    if not progress.total:
        last_page = __get_last_page(soup)
        if last_page:
            progress.total = int(last_page)
    progress.update()


def __update_thread_info(post_id, thread_info, post_dict):
    if not thread_info.get('first_post_id', ''):
        thread_info['first_post_id'] = post_id
        thread_info['title'] = post_dict.get('title')
        thread_info['author'] = post_dict.get('author', []).get('username')
        thread_info['author_id'] = post_dict.get('author', []).get('id', [])
