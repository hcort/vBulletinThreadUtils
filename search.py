from vBulletinThreadUtils.MessageFilter import MessageFilter
from vBulletinThreadUtils.vBulletinFileUtils import save_parse_result_as_file
from vBulletinThreadUtils.vBulletinSearch import start_searching
from vBulletinThreadUtils.vBulletinSession import vbulletin_session
from vBulletinThreadUtils.vBulletinThreadParserGen import thread_id_to_thread_link_dict, parse_thread


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
