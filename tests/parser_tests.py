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

from src import vBulletinThreadUtils


class ProgressVisorTQDM(vBulletinThreadUtils.ProgressVisor):
    """
        Uses the TQDM package as a progress visor
    """
    def __init__(self, message: str):
        super().__init__(message)
        self.__tqdm_progress = tqdm(position=0, leave=True, desc=f'Parsing {message}')

    @property
    def total(self):
        return self.total_iterations

    @property
    def initial(self):
        return self.__tqdm_progress.initial

    @initial.setter
    def initial(self, ini):
        self.__tqdm_progress.initial = ini

    @total.setter
    def total(self, total_iterations):
        super().__init__()
        self.__tqdm_progress.total = total_iterations

    def update(self, n=1):
        self.__tqdm_progress.update(n)


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
    thread_info = vBulletinThreadUtils.thread_id_to_thread_link_dict('9323203')
    progress_bar = ProgressVisorTQDM(thread_info['url'])
    if not vBulletinThreadUtils.vbulletin_session.output_dir:
        vBulletinThreadUtils.vbulletin_session.output_dir = '../output/'
    processor = vBulletinThreadUtils.MessageHTMLToHTMLFile()
    vBulletinThreadUtils.parse_thread(
        thread_info=thread_info, filter_obj=None, progress=progress_bar, post_processor=processor)
    # save_parse_result_as_file(thread_info=thread_info, save_to_index=False)


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
        vBulletinThreadUtils.thread_id_to_thread_link_dict('8728235'),
    ]
    if not vBulletinThreadUtils.vbulletin_session.output_dir:
        vBulletinThreadUtils.vbulletin_session.output_dir = '../output/'
    for item in thread_list:
        vBulletinThreadUtils.parse_thread(thread_info=item, filter_obj=None)
        vBulletinThreadUtils.save_parse_result_as_file(thread_info=item, save_to_index=True, thread_index_file='')


def thread_parsing_with_filter_by_post_author():
    """
        This test demonstrates the basic use of a MessageFilter object

        It works in the same way as simple_thread_parsing but the result
        will contain the messages that pass our criteria

        The filter object is a simple filter by post author
    """
    thread_info = vBulletinThreadUtils.thread_id_to_thread_link_dict('9036759')
    filter_obj = vBulletinThreadUtils.MessageFilterByAuthor('...')
    vBulletinThreadUtils.parse_thread(thread_info=thread_info, filter_obj=filter_obj)
    if not vBulletinThreadUtils.vbulletin_session.output_dir:
        vBulletinThreadUtils.vbulletin_session.output_dir = '../output/'
    vBulletinThreadUtils.save_parse_result_as_file(thread_info=thread_info, save_to_index=False)


def thread_parsing_convert_messages_to_BBCode():  # pylint: disable=invalid-name
    """
        This test demonstrates the basic use of a MessageProcessor object

        The previous tests used the basic behaviour of the parser, that stores
        each post as a HTML object.

        This HTML objects are useful to regenerate HTML files, as seen in previous
        texts but are hard to process

        In this test we will convert each message to its original BBCode
    """
    thread_info = vBulletinThreadUtils.thread_id_to_thread_link_dict('9036759')
    message_processor = vBulletinThreadUtils.MessageHTMLToBBCode()
    vBulletinThreadUtils.parse_thread(thread_info=thread_info, filter_obj=None, post_processor=message_processor)
    for idx, post_id in enumerate(thread_info['parsed_messages']):
        print(
            f'Post #{thread_info["parsed_messages"][post_id]["index"]} - '
            f'{thread_info["parsed_messages"][post_id]["author"]["username"]} - '
            f'{thread_info["parsed_messages"][post_id]["date"]}')
        print(thread_info['parsed_messages'][post_id]['message'])
        print('-----------------------------------------------------')
        if idx == 10:
            break


def thread_search_and_parse_convert_messages_to_plain_text():
    """
        This test demonstrates the basic use of a MessageProcessor object

        The previous tests used the basic behaviour of the parser, that stores
        each post as a HTML object.

        This HTML objects are useful to regenerate HTML files, as seen in previous
        texts but are hard to process

        In this test we will convert each message to its original BBCode
    """
    vBulletinThreadUtils.vbulletin_session.search_words = 'viviendas'
    vBulletinThreadUtils.vbulletin_session.subforum_id = '23'
    vBulletinThreadUtils.vbulletin_session.minimum_posts = '1000'
    vBulletinThreadUtils.vbulletin_session.output_dir = '../output/oraculo/'
    pickle_name = os.path.join(vBulletinThreadUtils.vbulletin_session.output_dir, 'search.pickle')
    if not os.path.exists(os.path.join(vBulletinThreadUtils.vbulletin_session.output_dir, 'search.pickle')):
        link_list = vBulletinThreadUtils.vBulletinSearch.search_selenium(
            driver=vBulletinThreadUtils.vbulletin_session.driver,
            search_query='viviendas',
            reply_number='1000',
            subforum='23')
        with open(pickle_name, 'wb') as file:
            pickle.dump(link_list, file)
    else:
        with open(pickle_name, 'rb') as file:
            link_list = pickle.load(file)
    message_processor = vBulletinThreadUtils.MessageHTMLToPlainText()
    filter_obj = vBulletinThreadUtils.MessageFilterByAuthor('...')
    for thread in link_list['links']:
        thread_info = vBulletinThreadUtils.thread_id_to_thread_link_dict(thread['id'])
        json_file = os.path.join(vBulletinThreadUtils.vbulletin_session.output_dir, f'{thread_info["id"]}.json')
        if not os.path.exists(json_file):
            vBulletinThreadUtils.parse_thread(
                thread_info=thread_info,
                filter_obj=filter_obj,
                post_processor=message_processor)
            with open(json_file, 'w', encoding='utf-8') as json_file:
                json.dump(thread_info, json_file)


def thread_parsing_convert_messages_to_plain_text():
    thread_info = vBulletinThreadUtils.thread_id_to_thread_link_dict('8865750')
    message_processor = vBulletinThreadUtils.MessageHTMLToPlainText()
    filter_obj = vBulletinThreadUtils.MessageFilterByAuthor('...')
    vBulletinThreadUtils.vbulletin_session.output_dir = './output/plain_text/'
    vBulletinThreadUtils.parse_thread(
        thread_info=thread_info,
        filter_obj=filter_obj,
        post_processor=message_processor)
    with open(os.path.join(vBulletinThreadUtils.vbulletin_session.output_dir,
                           f'{thread_info["id"]}.json'), 'w', encoding='utf-8') as json_file:
        json.dump(thread_info, json_file)


def thread_parsing_save_to_json_file():
    """
        In this test we store the parsing result as a json file instead of generating an HTML
        output similar to the parsed thread.
    """
    thread_ids = ['9580321', '9470612', '9605789', '9402444']
    thread_list = [vBulletinThreadUtils.thread_id_to_thread_link_dict(thread_id) for thread_id in thread_ids]
    if not vBulletinThreadUtils.vbulletin_session.output_dir:
        vBulletinThreadUtils.vbulletin_session.output_dir = '../output/'
    for item in thread_list:
        progress_bar = ProgressVisorTQDM(item['url'])
        vBulletinThreadUtils.parse_thread(
            thread_info=item,
            filter_obj=None,
            post_processor=vBulletinThreadUtils.MessageHTMLToText(),
            progress=progress_bar)
        with open(os.path.join(
                vBulletinThreadUtils.vbulletin_session.output_dir, f'{item["id"]}.json'),
                'w',
                encoding='utf-8') as json_file:
            json.dump(item, json_file)


def main():
    # from .vBulletinThreadUtils.vBulletinLoginSelenium import test_driver
    # test_driver()
    # create_list_and_delete()
    # simple_thread_parsing()
    # thread_info = thread_id_to_thread_link_dict('9323203')
    # from .vBulletinThreadUtils.vBulletinThreadParserGen import peek_thread_metadata
    # peek_thread_metadata(thread_info)
    # simple_thread_parsing_with_index_file()
    # thread_parsing_convert_messages_to_BBCode()
    # thread_parsing_convert_messages_to_PlainText()
    # thread_search_and_parse_convert_messages_to_PlainText()
    thread_parsing_save_to_json_file()


if __name__ == '__main__':
    main()
