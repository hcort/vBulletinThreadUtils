import os
import re
from urllib.parse import urlparse

import requests
from slugify import slugify

from MessageProcessor import MessageHTMLToText
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


def save_parse_result_as_file(thread_info):
    thread_messages = thread_info.get('parsed_messages', {})
    if not thread_messages:
        return
    thread_file = open_thread_file(thread_id=thread_info['id'],
                                   thread_name=thread_info['title'])
    for message in thread_messages:
        write_message_to_thread_file(thread_file=thread_file,
                                     thread_id=thread_info['id'],
                                     message_id=message,
                                     message=thread_messages[message])
    close_thread_file(thread_file)


def open_thread_file(thread_id, thread_name):
    output_dir = vbulletin_session.config['VBULLETIN'].get('output_dir', '')
    file_name = slugify('{}_{}'.format(thread_id, thread_name), max_length=250) if thread_name else thread_id
    thread_filename = os.path.join(output_dir, file_name + '.html')
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


full_message_template = '<table id="post{post_id}" class="tborder-author" style="table-layout: fixed; width: 100%;" ' \
                        'width="100%" cellspacing="0" cellpadding="5" border="0" align="center"\n' \
                        '   <tbody>\n' \
                        '       <tr>\n' \
                        '           <td class="thead" style="font-weight:normal; ' \
                        'border: 1px solid #D1D1D1; border-right: 0px" width="175">{post_date}</td>\n' \
                        '           <td class="thead" style="font-weight:normal; ' \
                        'border: 1px solid #D1D1D1; border-left: 0px" align="right">' \
                        '#<a href="{base_url}showthread.php?t={thread_id}#post{post_id}" ' \
                        'rel="nofollow" id="postcount{post_id}"' \
                        'name="{post_index}"><strong>{post_index}</strong></a></td>\n' \
                        '       </tr>\n' \
                        '       <tr valign="top">\n' \
                        '           <td class="alt2" rowspan="2" style="border: 1px solid #D1D1D1; ' \
                        'border-top: 0px; border-bottom: 0px" width="175"><div id="postmenu_{post_id}">' \
                        '<a class="bigusername" href="{base_url}member.php?u={user_id}">{user_name}</a></div>' \
                        '<div class="smallfont">&nbsp;<br><a href="{base_url}member.php?u={user_id}">' \
                        '<img id="fcterremoto" class="avatar" ' \
                        'src="{avatar_url}" ' \
                        'alt="Avatar de {user_name}" title="Avatar de {user_name}" ' \
                        'width="120" height="68" border="0"></a></div></td>\n' \
                        '{message_text}' \
                        '       </tr>\n' \
                        '   </tbody>\n' \
                        '</table>'

regex_post_id = re.compile("#post([0-9]+)")
regex_link_to_thread = re.compile("showthread\.php\?t=([0-9]+)")
regex_link_to_message = re.compile("showthread\.php\?p=([0-9]+)")
regex_link_to_profile = re.compile("member\.php\?u=([0-9]+)")


def fix_links_to_this_thread(thread_id, message):
    all_thread_links = message['HTML'].find_all('a', {'href': regex_link_to_thread}, recursive=True)
    for link in all_thread_links:
        href_val = link.attrs.get('href', '')
        m = regex_link_to_thread.search(href_val)
        if m and (m.group(1) == thread_id):
            post_id = regex_post_id.search(href_val)
            link.attrs['href'] = '#post{}'.format(post_id.group(1) if post_id else href_val)
        elif not urlparse(href_val).netloc:
            link.attrs['href'] = vbulletin_session.config['VBULLETIN']['base_url'] + href_val


def fix_links_to_posts_in_this_thread(message):
    all_posts_links = message['HTML'].find_all('a', {'href': regex_link_to_message}, recursive=True)
    for link in all_posts_links:
        post_id = regex_post_id.search(link.attrs.get('href', ''))
        if post_id:
            link.attrs['href'] = '#post{}'.format(post_id.group(1))


def fix_links_to_user_profiles(message):
    all_user_profiles = message['HTML'].find_all('a', {'href': regex_link_to_profile}, recursive=True)
    for link in all_user_profiles:
        if not urlparse(link.attrs.get('href', '')).netloc:
            link.attrs['href'] = vbulletin_session.confg['VBULLETIN']['base_url'] + link.attrs.get('href', '')


def fix_quotes_links(thread_id, message):
    if not message.get('HTML'):
        return
    """
        Takes links to this thread and convert them to anchor links so 
        I can navigate the thread totally offline.
        Fixes relative links to include the forum base URL
    """
    fix_links_to_this_thread(thread_id, message)
    fix_links_to_posts_in_this_thread(message)
    fix_links_to_user_profiles(message)
    html2text = MessageHTMLToText()
    return html2text.process_message(post_id='', message=message)


def write_message_to_thread_file(thread_file, thread_id, message_id, message):
    fixed_message = fix_quotes_links(thread_id, message)
    message = full_message_template.format(
        base_url=vbulletin_session.config['VBULLETIN']['base_url'],
        anchor_name=message_id,
        post_id=message_id,
        post_date=message['date'],
        thread_id=thread_id,
        post_index=message['index'],
        user_id=message['author']['id'],
        user_name=message['author']['username'],
        avatar_url=message['author']['avatar'],
        message_text=fixed_message
    )
    write_str_to_thread_file(thread_file=thread_file, table_str=message)


def write_str_to_thread_file(thread_file, table_str, retries=10):
    if retries > 0:
        try:
            thread_file.write(table_str)
            return True
        except UnicodeEncodeError as UniErr:
            # print(str(UniErr))
            if UniErr.reason == 'surrogates not allowed':
                # problema con codificación de emojis
                table_str_2 = table_str.encode('utf-8', errors='surrogatepass')
                return write_str_to_thread_file(thread_file, str(table_str_2, encoding='utf-8', errors='ignore'),
                                                retries - 1)
        except Exception as err:
            print(str(err))
    return False


def close_thread_file(thread_file):
    thread_file.write('\n</body></html>')
    thread_file.close()