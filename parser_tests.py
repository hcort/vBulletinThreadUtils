"""
    Some use examples of the utilities of vBulletinThreadUtils

    We'll need to create a configuration files under
        resources/config.ini

    This file must contain a set of minimal values:

    config.ini
    -----------------------------------------------------
    [VBULLETIN]
    logname = ...
    password = ...
    base_url = ...
    ; optional
    output_dir = ...
    -----------------------------------------------------

    In logname and password we must put valid credentials for the forum
    which we will be parsing.

    In base_url we'll put the basic domain of the vBulletin forum.
    It's usually in the form of https://www.some_forum.com/forum/

    To create the urls of the threads we will use this base_url value

    https://www.some_forum.com/forum/showthread.php?p=123456789#post987654321
    post_url = '{base_url}showthread.php?p={thread_id}#post{post_id}'

    As for output_dir is an optional value and it will be needed only when we
    are generating output files

"""
import json
import os
import pickle

from tqdm import tqdm

from vBulletinThreadUtils.MessageFilter import MessageFilterByAuthor
from vBulletinThreadUtils.MessageProcessor import MessageHTMLToBBCode, MessageHTMLToText, MessageHTMLToPlainText
from vBulletinThreadUtils.ProgressVisor import ProgressVisor
from vBulletinThreadUtils.vBulletinFileUtils import save_parse_result_as_file
from vBulletinThreadUtils.vBulletinSession import vbulletin_session
from vBulletinThreadUtils.vBulletinThreadParserGen import parse_thread, thread_id_to_thread_link_dict


class ProgressVisorTQDM(ProgressVisor):
    def __init__(self, message: str):
        super().__init__(message)
        self.__tqdm_progress = tqdm(position=0, leave=True, desc=f'Parsing {message}')

    @property
    def total(self):
        return self.total_iterations

    @total.setter
    def total(self, total_iterations):
        super().__init__(total_iterations)
        self.__tqdm_progress.total = total_iterations

    def update(self):
        self.__tqdm_progress.update()


def simple_thread_parsing():
    """
        This test demonstrates the basic use of a thread parser
        Given a thread id it will parse and save the thread in a local file

        First we will build the thread_info dictionary. This dictionary contains
        the minimal data we will need to parse a thread (thread id and thread url)

        Once the thread is parsed we check if there is an output_dir value in the
        config file. If not, we will save the file in a default folder (this folder
        must exist beforehand).

        Al last we save the file using save_parse_result_as_file

        We use the save_to_index=False to tell the method not to create or update the
        index file.
    """
    thread_info = thread_id_to_thread_link_dict('9036759')
    progress_bar = ProgressVisorTQDM(thread_info['url'])
    parse_thread(thread_info=thread_info, filter_obj=None, progress=progress_bar)
    if not vbulletin_session.output_dir:
        vbulletin_session.output_dir = './output/'
    save_parse_result_as_file(thread_info=thread_info, save_to_index=False)


def simple_thread_parsing_with_index_file():
    """
        This test is an extension of the previous test.

        In this case we will parse several threads and we will create an index file

        We use the save_to_index=True to tell the method to create or update the
        index file.

        As we don't pass a thread_index_file value the method will create a default index
        file under output_dir/saved_threads.html
    """
    thread_list = [
        thread_id_to_thread_link_dict('8959315'),
        thread_id_to_thread_link_dict('8987314'),
        thread_id_to_thread_link_dict('9012387'),
        thread_id_to_thread_link_dict('9040036'),
        thread_id_to_thread_link_dict('9067043')
    ]
    if not vbulletin_session.output_dir:
        vbulletin_session.output_dir = './output/'
    for item in thread_list:
        parse_thread(thread_info=item, filter_obj=None)
        save_parse_result_as_file(thread_info=item, save_to_index=True, thread_index_file='')


def thread_parsing_with_filter_by_post_author():
    """
        This test demonstrates the basic use of a MessageFilter object

        It works in the same way as simple_thread_parsing but the result
        will contain the messages that pass our criteria

        The filter object is a simple filter by post author
    """
    thread_info = thread_id_to_thread_link_dict('9036759')
    filter_obj = MessageFilterByAuthor('castelo')
    parse_thread(thread_info=thread_info, filter_obj=filter_obj)
    if not vbulletin_session.output_dir:
        vbulletin_session.output_dir = './output/'
    save_parse_result_as_file(thread_info=thread_info, save_to_index=False)


def thread_parsing_convert_messages_to_BBCode():
    """
        This test demonstrates the basic use of a MessageProcessor object

        The previous tests used the basic behaviour of the parser, that stores
        each post as a HTML object.

        This HTML objects are useful to regenerate HTML files, as seen in previous
        texts but are hard to process

        In this test we will convert each message to its original BBCode
    """
    thread_info = thread_id_to_thread_link_dict('9036759')
    message_processor = MessageHTMLToBBCode()
    parse_thread(thread_info=thread_info, filter_obj=None, post_processor=message_processor)
    for idx, post_id in enumerate(thread_info['parsed_messages']):
        print('Post #{} - {} - {}'.format(thread_info['parsed_messages'][post_id]['index'],
                                          thread_info['parsed_messages'][post_id]['author']['username'],
                                          thread_info['parsed_messages'][post_id]['date']))
        print(thread_info['parsed_messages'][post_id]['message'])
        print('-----------------------------------------------------')
        if idx == 10:
            break


def thread_search_and_parse_convert_messages_to_PlainText():
    """
        This test demonstrates the basic use of a MessageProcessor object

        The previous tests used the basic behaviour of the parser, that stores
        each post as a HTML object.

        This HTML objects are useful to regenerate HTML files, as seen in previous
        texts but are hard to process

        In this test we will convert each message to its original BBCode
    """
    vbulletin_session.search_words = 'viviendas'
    vbulletin_session.subforum_id = '23'
    vbulletin_session.minimum_posts = '1000'
    vbulletin_session.output_dir = './output/oraculo/'
    if not os.path.exists(os.path.join(vbulletin_session.output_dir, 'searchu.pickle')):
        from vBulletinThreadUtils.vBulletinSearch import start_searching
        link_list = start_searching()
        with open(os.path.join(vbulletin_session.output_dir, 'search.pickle'), 'wb') as file:
            pickle.dump(link_list, file)
    else:
        with open(os.path.join(vbulletin_session.output_dir, 'search.pickle'), 'rb') as file:
            link_list = pickle.load(file)
    message_processor = MessageHTMLToPlainText()
    # filter_obj = MessageFilterByAuthor('eugim')
    # vbulletin_session.output_dir = './output/fraude/'
    filter_obj = MessageFilterByAuthor('kaplane')
    for thread in link_list['links']:
        thread_info = thread_id_to_thread_link_dict(thread['id'])
        json_file = os.path.join(vbulletin_session.output_dir, f'{thread_info["id"]}.json')
        if not os.path.exists(json_file):
            parse_thread(thread_info=thread_info, filter_obj=filter_obj, post_processor=message_processor)
            with open(json_file, 'w', encoding='utf-8') as json_file:
                json.dump(thread_info, json_file)


def thread_parsing_convert_messages_to_PlainText():
    thread_info = thread_id_to_thread_link_dict('8865750')
    message_processor = MessageHTMLToPlainText()
    filter_obj = MessageFilterByAuthor('eugim')
    vbulletin_session.output_dir = './output/fraude_mayor/'
    parse_thread(thread_info=thread_info, filter_obj=filter_obj, post_processor=message_processor)
    with open(os.path.join(vbulletin_session.output_dir,
                           f'{thread_info["id"]}.json'), 'w', encoding='utf-8') as json_file:
        json.dump(thread_info, json_file)


def thread_parsing_save_to_json_file():
    """
        In this test we store the parsing result as a json file instead of generating an HTML
        output similar to the parsed thread.
    """
    thread_ids = ['8875858', '6916796']
    thread_list = [thread_id_to_thread_link_dict(thread_id) for thread_id in thread_ids]
    if not vbulletin_session.output_dir:
        vbulletin_session.output_dir = './output/'
    filter_obj = MessageFilterByAuthor('@OP')
    bs4_tag_to_str = MessageHTMLToText()
    bs4_tag_to_bbcode = MessageHTMLToBBCode()
    for item in thread_list:
        parse_thread(thread_info=item, filter_obj=filter_obj)
        for msg in item['parsed_messages']:
            bs4_tag = item['parsed_messages'][msg]['message']
            msg_as_text = bs4_tag_to_str.process_message('', bs4_tag)
            msg_as_bbcode = bs4_tag_to_bbcode.process_message('', bs4_tag)
            item['parsed_messages'][msg]['message'] = None
            item['parsed_messages'][msg]['html_str'] = msg_as_text
            item['parsed_messages'][msg]['bbcode'] = msg_as_bbcode
        with open(os.path.join(vbulletin_session.output_dir, f'{item["id"]}.json'), 'w', encoding='utf-8') as json_file:
            json.dump(item, json_file)


def main():
    simple_thread_parsing()
    # simple_thread_parsing_with_index_file()
    # thread_parsing_convert_messages_to_BBCode()
    # thread_parsing_convert_messages_to_PlainText()
    # thread_search_and_parse_convert_messages_to_PlainText()
    # thread_parsing_save_to_json_file()


if __name__ == "__main__":
    main()
