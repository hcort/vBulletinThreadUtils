import os

from vBulletinSession import vbulletin_session
from vBulletinThreadParser import VBulletinThreadParser


class VBulletinUserMessagesByThread(object):

    def __init__(self, base_url):
        self.__index_file = None
        self.__base_url = base_url

    def find_user_messages(self, links, username):
        num_links = len(links)
        for idx, link in enumerate(links):
            print('[' + str(idx) + '/' + str(num_links) + '] - ' + str(link))
            thread_name = link['title']
            thread_parser = VBulletinThreadParser(self.__base_url, thread_name, username)
            author_matches = thread_parser.parse_thread(link['url'])
            link['matches'] = author_matches

    def open_index_file(self):
        filename = os.path.join('output', 'index.html')
        if os.path.exists(filename):
            os.remove(filename)
        # 'iso-8859-1', 'cp1252'
        if not self.__index_file:
            self.__index_file = open(filename, "a+", encoding='utf-8')
        for line in open(os.path.join('resources', 'search_index_header.txt'), "r"):
            self.__index_file.write(line)

    def close_index_file(self):
        self.__index_file.write('</table></body></html>')
        self.__index_file.close()
        self.__index_file = None

    def create_index_page(self, links):
        with open(os.path.join('resources', 'index_file_entry_patter.txt'), 'r') as file:
            entry_pattern = file.read()
        self.open_index_file()
        for idx, link in enumerate(links):
            link_pattern = entry_pattern
            link_pattern = link_pattern.replace('{idx_link}', str(idx))
            link_pattern = link_pattern.replace('{id}', link['id'])
            link_pattern = link_pattern.replace('{url}', link['url'])
            link_pattern = link_pattern.replace('{title}', link['title'])
            link_pattern = link_pattern.replace('{hover}', link['hover'])
            link_pattern = link_pattern.replace('{author}', link['author'])
            link_pattern = link_pattern.replace('{author_id}', link['author_id'])
            link_pattern = link_pattern.replace('{author_matches}', str(link['matches']))
            self.__index_file.write(link_pattern)
        self.close_index_file()
