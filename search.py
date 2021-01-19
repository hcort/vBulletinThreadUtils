import getopt
import sys

from vBulletinSearch import VBulletinSearch
from vBulletinThreadDateParser import find_user_message_timestamp
from vBulletingUserMessagesByThread import VBulletinUserMessagesByThread


def main():
    username = ''
    pwd = ''
    usr = ''
    argv = sys.argv[1:]
    # TODO https://docs.python.org/3/library/configparser.html
    try:
        opts, args = getopt.getopt(argv, 'u:p:t:')
        for (opt, value) in opts:
            if opt == "-u":
                username = str(value)
            elif opt == "-p":
                pwd = str(value)
            elif opt == "-t":
                usr = str(value)
    except ValueError as err:
        print(str(err))
        exit(-1)

    if not username or not pwd or not usr:
        exit()

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
    parser = VBulletinSearch(login_data=login_data)
    link_list = parser.start_searching(usr)
    timestamp = True
    if timestamp:
        find_user_message_timestamp(link_list, username)
    else:
        thread_parser = VBulletinUserMessagesByThread(parser.session, parser.base_url)
        thread_parser.find_user_messages(link_list, username)
        thread_parser.create_index_page(link_list)


# Lanzamos la función principal
if __name__ == "__main__":
    main()
