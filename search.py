import configparser
import getopt
import os
import sys

from vBulletinLogin import VBulletinLogin
from vBulletinSearch import VBulletinSearch
from vBulletinThreadDateParser import find_user_message_timestamp
from vBulletingUserMessagesByThread import VBulletinUserMessagesByThread


def main():
    username = ''
    pwd = ''
    # TODO https://docs.python.org/3/library/configparser.html
    config = configparser.ConfigParser()
    config.read(os.path.join('resources', 'config.ini'), encoding='utf-8')

    try:
        # TODO username and pwd may not be needed in public threads
        username = config['VBULLETIN']['logname']
        pwd = config['VBULLETIN']['password']
        base_url = config['VBULLETIN']['base_url']
        operation_mode = config['OPERATIONMODE']['operation']
    except KeyError as err:
        print('Missing config entries: ' + str(err))
        exit(-1)

    # This is the form data that the page sends when logging in
    login_data = {
        'do': 'login',
        'forceredirect': '0',
        'url': '',
        'vb_login_md5password': '',
        'vb_login_md5password_utf': '',
        's': '',
        'securitytoken': 'guest',
        'vb_login_username': username,
        'vb_login_password': pwd,
        'cookieuser': '1',
        'logb2': 'Acceder'}
    session = VBulletinLogin(base_url + 'login.php', login_data)
    if not session:
        exit()

    filter_usr = config['FILTERUSER'].get('username', '')
    search_user = config['SEARCHTHREADS'].get('searchuser', '')
    search_query = config['SEARCHTHREADS'].get('search_words', '')
    strict_search = config['SEARCHTHREADS'].get('strict_search', False)

    if operation_mode == 'SEARCHTHREADS':
        parser = VBulletinSearch(session, base_url)
        link_list = parser.start_searching(search_query, search_user, strict_search)
        thread_parser = VBulletinUserMessagesByThread()
        thread_parser.find_user_messages(link_list, filter_usr)
        thread_parser.create_index_page(link_list)
    elif operation_mode == 'TIMESTAMP':
        parser = VBulletinSearch(session)
        link_list = parser.start_searching(search_query=search_query, thread_author=search_user)
        find_user_message_timestamp(link_list, filter_usr)
    elif operation_mode == 'SINGLETHREAD':
        # extraer {'id': '', 'url': '', 'title': '', 'hover': '', 'author': '', 'author_id': ''}
        thid = config['SINGLETHREAD']['thread_id']
        this_thread = {
            'id': thid,
            'url': base_url + 'showthread.php?t=' + thid,
            'title': '',
            'hover': '',
            'author': '',
            'author_id': ''
        }
        # FIXME get thread title
        link_list = [this_thread]
        thread_parser = VBulletinUserMessagesByThread(session, base_url)
        thread_parser.find_user_messages(link_list, filter_usr)
    else:
        print('Operation mode: ' + operation_mode + ' unknown')


# Lanzamos la función principal
if __name__ == "__main__":
    main()
