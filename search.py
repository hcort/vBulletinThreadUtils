import configparser
import os

from vBulletinLogin import VBulletinLogin
from vBulletinSearch import VBulletinSearch
from vBulletinThreadDateParser import find_user_message_timestamp
from vBulletinWordCloud import find_user_message_wordcloud
from vBulletingUserMessagesByThread import VBulletinUserMessagesByThread


def thread_id_to_thread_link_dict(config, thread_id):
    return {
                'id': thread_id,
                'url': '{base}/showthread.php?t={thread_id}'.format(base=config['VBULLETIN'].get('base_url', ''), thread_id=thread_id),
                'title': '',
                'hover': '',
                'author': '',
                'author_id': ''
            }


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
        's': 'f6a6b3226a64c319a11efd886f798259',
        'securitytoken': 'guest',
        'vb_login_username': username,
        'vb_login_password': pwd,
        'cookieuser': '1',
        'logb2': 'Acceder'}
    # FIXME retrasar la creación de la sesión hasta el último momento
    # login_url = 'https://www.forocoches.com/foro/misc.php?do=page&template=ident'
    session = VBulletinLogin(base_url + 'login.php', login_data)
    if not session:
        exit()

    filter_usr = config['FILTERUSER'].get('username', '')
    search_user = config['SEARCHTHREADS'].get('searchuser', '')
    search_query = config['SEARCHTHREADS'].get('search_words', '')
    strict_search = config['SEARCHTHREADS'].get('strict_search', False)

    save_images = (config['VBULLETIN'].get('save_images', '') == 'True')
    output_dir = config['VBULLETIN'].get('output_dir', '')
    server_root = config['VBULLETIN'].get('http_server_root', output_dir)

    if operation_mode == 'SEARCHTHREADS':
        parser = VBulletinSearch(session, base_url)
        link_list = parser.start_searching(search_query, search_user, strict_search)
        thread_parser = VBulletinUserMessagesByThread()
        thread_parser.find_user_messages(link_list, filter_usr,
                                         save_images=save_images, output_dir=output_dir, server_root=server_root)
        thread_parser.create_index_page(link_list)
    elif operation_mode == 'TIMESTAMP':
        parser = VBulletinSearch(session)
        link_list = parser.start_searching(search_query=search_query, thread_author=search_user)
        find_user_message_timestamp(link_list, filter_usr)
    elif operation_mode == 'WORDCLOUD':
        # un único hilo o una búsqueda (?)
        if config[operation_mode].get('thread_id', ''):
            link_list = [thread_id_to_thread_link_dict(config, config[operation_mode].get('thread_id', ''))]
        elif config[operation_mode].get('thread_list', ''):
            thread_list = config[operation_mode].get('thread_list', '').split(',')
            link_list = []
            for thread in thread_list:
                link_list.append(thread_id_to_thread_link_dict(config, thread))
        else:
            parser = VBulletinSearch(session)
            link_list = parser.start_searching(search_query=search_query, thread_author=search_user, strict_search=strict_search)
        find_user_message_wordcloud(link_list, filter_usr, base_url, session)
    elif operation_mode == 'SINGLETHREAD':
        link_list = [thread_id_to_thread_link_dict(config, config[operation_mode].get('thread_id', ''))]
        thread_parser = VBulletinUserMessagesByThread(session, base_url)
        thread_parser.find_user_messages(link_list, filter_usr,
                                         save_images=save_images, output_dir=output_dir, server_root=server_root)
    else:
        print('Operation mode: ' + operation_mode + ' unknown')


if __name__ == "__main__":
    main()
