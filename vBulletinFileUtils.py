import os
import re

import requests
from slugify import slugify

from vBulletinSession import vbulletin_session


def open_index_file():
    # FIXME buscar manera de crear un indice individual
    output_dir = vbulletin_session.config['VBULLETIN'].get('output_dir', '')
    filename = os.path.join(output_dir, 'index.html')
    if os.path.exists(filename):
        os.remove(filename)
    # 'iso-8859-1', 'cp1252'
    index_file = open(filename, "a+", encoding='utf-8')
    for line in open(os.path.join('resources', 'search_index_header.txt'), "r"):
        index_file.write(line)
    return index_file


def save_search_results_as_index_page(links):
    with open(os.path.join('resources', 'index_file_entry_patter.txt'), 'r') as file:
        entry_pattern = file.read()
    index_file = open_index_file()
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
        index_file.write(link_pattern)
    index_file.write('</table></body></html>')
    index_file.close()


def save_image(src_txt, output_dir='', server_root=''):
    output_dir = vbulletin_session.config['VBULLETIN'].get('output_dir', '')
    server_root = vbulletin_session.config['VBULLETIN'].get('http_server_root', output_dir)
    img_filename = slugify(src_txt, max_length=250)
    image_path = os.path.join(output_dir, 'imgs', img_filename)
    # server_root is used to build the new img src attribute so a local
    # http server can display them properly
    if server_root:
        rel_path = os.path.relpath(output_dir, server_root)
        image_src_new = os.path.join('\\', rel_path, 'imgs', img_filename)
    else:
        image_src_new = image_path
    if not os.path.exists(image_path):
        with open(image_path, 'wb') as handle:
            try:
                response = requests.get(src_txt, stream=True)
                if not response.ok:
                    print('Error getting image: ' + src_txt)
                for block in response.iter_content(1024):
                    if not block:
                        break
                    handle.write(block)
                return image_src_new
            except ConnectionError as err:
                print('Error getting image: ' + src_txt)
                print(err)
            except Exception as err:
                print('Error getting image: ' + src_txt)
                print(err)
    else:
        return image_src_new
    return src_txt


def open_thread_file(thread_url, thread_id, thread_name):
    output_dir = vbulletin_session.config['VBULLETIN'].get('output_dir', '')
    regex_id = re.compile("t=([0-9]+)")
    thread_filename = os.path.join(output_dir, thread_id + '.html')
    if os.path.exists(thread_filename):
        os.remove(thread_filename)
    # 'iso-8859-1', 'cp1252'
    thread_file = open(thread_filename, "a+", encoding='latin-1')
    for line in open(os.path.join('resources', "page_header.txt"), "r"):
        if line.startswith('<meta name="description"'):
            thread_file.write(
                '<meta name=\"description\" content=\"{}\" />'.format(thread_name))
        elif line.startswith('<title>'):
            thread_file.write('<title>' + thread_name + '</title>')
        else:
            thread_file.write(line)
    return thread_file


def write_str_to_thread_file(thread_file, table_str, retries=10):
    if retries > 0:
        try:
            thread_file.write(table_str)
            return True
        except UnicodeEncodeError as UniErr:
            print(str(UniErr))
            if UniErr.reason == 'surrogates not allowed':
                # problema con codificación de emojis
                table_str_2 = table_str.encode('utf-8', errors='surrogatepass')
                return write_str_to_thread_file(thread_file, str(table_str_2, encoding='utf-8', errors='ignore'), retries - 1)
        except Exception as err:
            print(str(err))
    return False


def close_thread_file(thread_file):
    thread_file.write('\n</body></html>')
    thread_file.close()
