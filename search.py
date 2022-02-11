from vBulletinSearch import VBulletinSearch
from vBulletinSession import vbulletin_session
from vBulletinThreadDateParser import find_user_message_timestamp
from vBulletinWordCloud import find_user_message_wordcloud
from vBulletingUserMessagesByThread import VBulletinUserMessagesByThread


def thread_id_to_thread_link_dict(thread_id):
    return {
                'id': thread_id,
                'url': '{base}/showthread.php?t={thread_id}'.format(
                    base=vbulletin_session.config['VBULLETIN'].get('base_url', ''), thread_id=thread_id),
                'title': '',
                'hover': '',
                'author': '',
                'author_id': ''
            }


def create_link_list():
    operation_mode = vbulletin_session.config['OPERATIONMODE']['operation']
    if vbulletin_session.config[operation_mode].get('thread_id', ''):
        link_list = [thread_id_to_thread_link_dict(vbulletin_session.config[operation_mode].get('thread_id', ''))]
    elif vbulletin_session.config[operation_mode].get('thread_list', ''):
        thread_list = vbulletin_session.config[operation_mode].get('thread_list', '').split(',')
        link_list = []
        for thread in thread_list:
            link_list.append(thread_id_to_thread_link_dict(thread))
    else:
        base_url = vbulletin_session.config['VBULLETIN']['base_url']
        parser = VBulletinSearch(base_url)
        link_list = parser.start_searching()
    return link_list


def main():
    operation_mode = vbulletin_session.config['OPERATIONMODE']['operation']
    base_url = vbulletin_session.config['VBULLETIN']['base_url']

    filter_usr = vbulletin_session.config['FILTERUSER'].get('username', '')

    link_list = create_link_list()

    if operation_mode == 'SEARCHTHREADS':
        thread_parser = VBulletinUserMessagesByThread(base_url)
        thread_parser.find_user_messages(link_list, filter_usr)
        thread_parser.create_index_page(link_list)
    elif operation_mode == 'TIMESTAMP':
        find_user_message_timestamp(link_list, filter_usr)
    elif operation_mode == 'WORDCLOUD':
        find_user_message_wordcloud(link_list, filter_usr, base_url)
    elif operation_mode == 'SINGLETHREAD':
        thread_parser = VBulletinUserMessagesByThread(base_url)
        thread_parser.find_user_messages(link_list, filter_usr)
    else:
        print('Operation mode: ' + operation_mode + ' unknown')


if __name__ == "__main__":
    main()
