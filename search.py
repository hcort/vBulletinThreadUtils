from vBulletinThreadUtils.vBulletinSearch import start_searching
from vBulletinThreadUtils.vBulletinSession import vbulletin_session
from vBulletinThreadUtils.vBulletinThreadParserGen import find_user_messages_in_thread_list, \
    thread_id_to_thread_link_dict


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
    base_url = vbulletin_session.base_url

    filter_usr = vbulletin_session.config['FILTERUSER'].get('username', '')

    link_list = create_link_list()
    if not link_list:
        return

    if operation_mode == 'SEARCHTHREADS':
        # link list should be a dict link_list{'search_id', 'links'}
        index_file = 'search_{}_index.html'.format(link_list.get('search_id', ''))
        find_user_messages_in_thread_list(link_list['links'], filter_usr, thread_index_file=index_file)
    elif operation_mode == 'SINGLETHREAD':
        find_user_messages_in_thread_list(link_list, filter_usr)
    else:
        print('Operation mode: ' + operation_mode + ' unknown')


if __name__ == "__main__":
    main()
