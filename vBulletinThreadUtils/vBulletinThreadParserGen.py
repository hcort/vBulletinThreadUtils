import datetime
import re

from bs4 import BeautifulSoup, Tag

from vBulletinThreadUtils import MessageFilter, MessageProcessor
from vBulletinThreadUtils.ProgressVisor import ProgressVisor
from vBulletinThreadUtils.utils import (get_soup_requests,
                                        normalize_date_string_vbulletin_format,
                                        normalize_date_string,
                                        get_string_from_regex)
from vBulletinThreadUtils.vBulletinSession import vbulletin_session


def thread_id_to_thread_link_dict(thread_id):
    """
    Builds an empty thread_info dictionary with just thread_id and url values

    :param thread_id:
    :return: a thread_info dictionary in a format expected by the parse_thread method
    """
    return {
        'id': thread_id,
        'url': f'{vbulletin_session.base_url}/showthread.php?t={thread_id}',
        'title': '',
        'hover': '',
        'author': '',
        'author_id': ''
    }


def peek_thread_metadata(thread_info: dict = None) -> None:
    """

    :param thread_info:
    :return: None

    The result of the peek operation is stored in the thread_info dictionary

    Fields of thread_info filled:

        thread_info['creation_date']
        thread_info['modification_date']
        thread_info['message_count']

        thread_info['author']
        thread_info['author_id']
        thread_info['first_post_id']

    """
    if not vbulletin_session.session or not thread_info:
        return None
    soup = get_soup_requests(thread_info.get('url', ''))
    if not soup:
        return None

    thread_info['parsed_messages'] = {}
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
                 progress: ProgressVisor = None) -> None:
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
        The parser will parse messages #51, #52, ..., #59 and #60, but it won't store them in the output. The
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
    current_url = thread_info.get('url', '')
    if thread_info.get('last_page', ''):
        current_url = f'{current_url}&page={thread_info["last_page"]}'
    if not vbulletin_session.session or not current_url:
        return

    if not thread_info.get('parsed_messages', None):
        thread_info['parsed_messages'] = {}

    if progress and thread_info.get('last_page', None):
        progress.update(n=thread_info["last_page"])
    soup = None
    while current_url:
        soup = get_soup_requests(current_url)
        if not soup:
            break
        __update_progress_bar(progress, soup)
        __search_and_parse_messages(thread_info, soup, filter_obj, current_url, post_processor)
        thread_info["last_page"] = __get_page_number_from_url(current_url)
        next_url = __get_next_url(soup)
        # FIXME sometimes current_url is a "ghost page" that contains the same messages as the previous one
        current_url = next_url if next_url != current_url else None
    __update_thread_timestamps(thread_info, soup)


regex_page_number = re.compile(r'page=([0-9]+)')
regex_user_id = re.compile(r'\?u=([0-9]+)')
regex_date_published = re.compile(r'datePublished":\s*"([\d\-T\+:]{25})')
regex_date_modified = re.compile(r'dateModified":\s*"([\d\-T\+:]{25})')
regex_interaction_count = re.compile(r'userInteractionCount":\s*"(\d+)"')
regex_message_index = re.compile(r'postcount[0-9]+')
regex_message_table = re.compile(r'td_post_[0-9]+')
regex_message_id = re.compile(r'#post([0-9]+)')


def __update_thread_timestamps(thread_info: dict, soup: BeautifulSoup) -> None:
    """
        Extracts metadata about the thread:
            - creation date
            - modification date
            - message count

    :param thread_info: The dictionary that contains the data extracted from the thread
    :param soup: The HTML structure of the current page
    :return: Nothing
    """
    if (not soup) or thread_info.get('creation_date', ''):
        return
    all_script_data = soup.find_all('script', {'type': 'application/ld+json'})
    json_type_str = '"@type":"DiscussionForumPosting"'
    for data in all_script_data:
        type_pos = data.text.find(json_type_str, 30, 90)
        if type_pos >= 0:
            thread_info['creation_date'] = normalize_date_string(
                get_string_from_regex(regex_date_published, data.text))
            thread_info['modification_date'] = normalize_date_string(
                get_string_from_regex(regex_date_modified, data.text))
            thread_info['message_count'] = int(get_string_from_regex(regex_interaction_count, data.text))

            first_msg_id = thread_info.get('first_post_id', None)
            first_message_time = thread_info['parsed_messages'][first_msg_id]['date'] if first_msg_id else (
                thread_info)['creation_date']
            if first_message_time != thread_info['creation_date']:
                delta_hour = datetime.datetime.strptime(first_message_time, '%Y-%m-%d - %H:%M') - \
                             datetime.datetime.strptime(thread_info['creation_date'], '%Y-%m-%d - %H:%M')
                thread_info['creation_date'] = first_message_time
                thread_info['modification_date'] = \
                    (datetime.datetime.strptime(thread_info['modification_date'], '%Y-%m-%d - %H:%M') +
                     delta_hour).strftime('%Y-%m-%d - %H:%M')


def __get_post_title(msg: Tag) -> str:
    """
        The title of the post is optional

    :param msg: The Tag with the post content
    :return: the title or empty string
    """
    title_node = msg.select_one('div:nth-of-type(1) > strong')
    return title_node.text if title_node else ''


def __remove_other_tags_from_msg(msg: Tag) -> None:
    """
        Given the HTML structure of a post we have to remove some irrelevant content
        that appears before the start of the message

    :param msg: The Tag with the post content
    :return: Nothing
    """
    decomposed_tags = 0
    for idx, child in enumerate(msg.children):
        if isinstance(child, Tag) and child.get('id', '').startswith('post_message_'):
            decomposed_tags = idx
            break
    msg.contents = msg.contents[decomposed_tags + 1:]


def __get_post_author_info(user_info: Tag, post_user_is_op: bool = False) -> dict:
    user_info_len = len(user_info.contents)
    post_user_name = user_info.contents[3].text.strip() if user_info_len > 3 else ''
    user_id = ''
    post_user_avatar = ''
    if user_info_len > 7:
        profile_link = user_info.contents[7].find('a')
        user_id = get_string_from_regex(regex_user_id, profile_link.get('href', '') if profile_link else '')
        avatar_img = user_info.contents[7].find('img')
        post_user_avatar = avatar_img.get('src', '') if avatar_img else ''
    # TODO user phrase in user_info.contents[5], user reg date and user location in user_info.contents[9]
    return {
        'id': user_id,
        'username': post_user_name,
        'is_op': post_user_is_op,
        'avatar': post_user_avatar
    }


def __search_and_parse_messages(thread_info, soup, filter_obj, current_url, post_processor):
    """
        A message is composed of:
            - Username
            - User profile URL (it has the user id in it)
            - User avatar URL
            - Date
            - Index (relative index in the thread)
            - Message title (optional)
            - Message body

        In this function we retrieve the list of all messages in the page and process them one by one

    :param thread_info: The dictionary object with all the parsed data from the thread
    :param soup: The HTML object
    :param filter_obj: See MessageFilter
    :param current_url: the URL of the page we are processing now
    :param post_processor: See MessageProcessor
    :return:
    """
    all_message_indexes = soup.find_all('a', {'id': regex_message_index})
    all_messages = soup.find_all('td', {'id': regex_message_table})
    all_dates = soup.select('table[class^=tborder] td.thead:nth-child(1)')
    all_user_info = soup.select('table[id^=post] > tr:nth-child(2) > td:nth-child(1)')
    try:
        for idx, msg, post_date, user_info in list(zip(all_message_indexes,
                                                       all_messages,
                                                       all_dates,
                                                       all_user_info)):
            current_post = {
                'link': idx.get('href', ''),
                'index': idx.text,
                'title': __get_post_title(msg),
                'date': __fix_post_date(post_date.text.strip())
            }
            __remove_other_tags_from_msg(msg)
            post_user_is_op = 'alt1-author' in msg.get('class', [])
            current_post['author'] = __get_post_author_info(user_info, post_user_is_op)

            # I want to have the message metadata in the dictionary before calling the post-processor
            post_id = get_string_from_regex(regex_message_id, current_post['link'])
            thread_info['parsed_messages'][post_id] = current_post

            saved_message = msg if not post_processor else \
                post_processor.process_message(thread_info=thread_info, post_id=post_id, message=msg)
            thread_info['parsed_messages'][post_id]['message'] = saved_message

            if current_post and ((not filter_obj) or (filter_obj and
                                                      (filter_obj.filter_message(post_id, current_post)))):
                thread_info['last_message'] = current_post.get('index', 0)
            else:
                thread_info['parsed_messages'].pop(post_id)
            __update_first_post_id_info(thread_info, post_id, current_post)
    except Exception as err:
        print(f'Error in thread {current_url} - {err}')


def __get_next_url(soup: BeautifulSoup) -> str:
    next_link = soup.select_one('a[rel="next"]')
    return f"{vbulletin_session.base_url}{next_link.get('href', '')}" if next_link else ''


def __fix_post_date(date_string: str) -> str:
    """
        Handles some formatting of dates in Spanish.
        Most recent post may have a date like "Hoy, 13:37" or "Ayer, 23:50"

    :param date_string: The date retrieved from the post
    :return: A normalized date string
    """
    # FIXME locale https://stackoverflow.com/questions/985505/locale-date-formatting-in-python
    [date_str, hour_str] = date_string.split(',')
    return normalize_date_string_vbulletin_format(date_str, hour_str)
    # if (date_string[0] == 'H') or (date_string[0] == 'A'):
    #     locale.setlocale(locale.LC_ALL, 'es_ES')
    #     dia = datetime.now() if date_string[0] == 'H' else datetime.now() - datetime.timedelta(days=1)
    #     return f"{dia.year}-{dia.month}-{dia.day} - {date_string.split(',')[1]}"
    # else:
    #     return normalize_date_string_vbulletin_format(date_string)


def __get_page_number_from_url(url):
    return get_string_from_regex(regex_page_number, url)


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


def __update_first_post_id_info(thread_info, post_id: str = None, post_dict: dict = None):
    if not thread_info.get('first_post_id', None):
        if not thread_info.get('parsed_messages', None):
            return
        if not post_id:
            post_id = next(iter(thread_info['parsed_messages']))
        if not post_dict:
            post_dict = thread_info['parsed_messages'][post_id]
        thread_info['first_post_id'] = post_id
        thread_info['title'] = post_dict.get('title')
        thread_info['author'] = post_dict.get('author', []).get('username')
        thread_info['author_id'] = post_dict.get('author', []).get('id', [])
