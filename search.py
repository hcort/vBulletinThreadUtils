from vBulletinSearch import start_searching
from vBulletinSession import vbulletin_session
from vBulletinThreadDateParser import find_user_message_timestamp
from vBulletinThreadParserGen import find_user_messages_in_thread_list
from vBulletinWordCloud import find_user_message_wordcloud
from vBulletinFileUtils import save_search_results_as_index_page


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
            link_list.append(thread_id_to_thread_link_dict(thread.strip()))
    else:
        link_list = start_searching()
    return link_list


def main():
    operation_mode = vbulletin_session.config['OPERATIONMODE']['operation']
    base_url = vbulletin_session.config['VBULLETIN']['base_url']

    filter_usr = vbulletin_session.config['FILTERUSER'].get('username', '')

    link_list = create_link_list()

    if operation_mode == 'SEARCHTHREADS':
        # link list should be a dict link_list{'search_id', 'links'}
        index_file = 'search_{}_index.html'.format(link_list.get('search_id', ''))
        find_user_messages_in_thread_list(link_list['links'], filter_usr, thread_index_file=index_file)
    elif operation_mode == 'TIMESTAMP':
        find_user_message_timestamp(link_list, filter_usr)
    elif operation_mode == 'WORDCLOUD':
        find_user_message_wordcloud(link_list, filter_usr, base_url)
    elif operation_mode == 'SINGLETHREAD':
        find_user_messages_in_thread_list(link_list, filter_usr)
    else:
        print('Operation mode: ' + operation_mode + ' unknown')


if __name__ == "__main__":
    main()
