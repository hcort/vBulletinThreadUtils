import re

from bs4 import NavigableString, Tag

regex_mention_user = re.compile("member.php\?u=([0-9]+)")
regex_quote_user = re.compile("showthread.php\?p=[0-9]+#post([0-9]+)")
regex_youtube_script = re.compile("verVideo\(\\'([\w\-]+)\\'")
regex_instagram_permalink = re.compile("/p/([\w]+)/")

"""
    TODO
    
    pending tags
    
    [VOCAROO][/VOCAROO]
    [TIKTOK][/TIKTOK]
    [FB][/FB]
    [CODE][/CODE]
    
    [INDENT][/INDENT]

    [LEFT]alineación izquierda[/LEFT]    
    [CENTER]alineación centro[/CENTER]    
    [RIGHT]alineación derecha[/RIGHT]  
    
    [COLOR=Red]texto con color[/COLOR]    
    [COLOR=Red][B]color y negrita[/B][/COLOR]

    <div align="left">alineación izquierda</div>
    <div align="center">alineación centro</div>
    <div align="right">alineación derecha</div>
    
    <font color="Red">texto con color</font>
    <font color="Red"><b>color y negrita</b></font>
"""


def parseHTMLnode(child):
    # print(child)
    if child.name == 'br':
        return '\n'
    if child.isSelfClosing and (child.name != 'img'):
        # FIXME <hr>
        return ''
    if child.get('id', '').startswith('post_message_'):
        return ''
    formatted_text = parse_formatted_text(child)
    if formatted_text:
        return formatted_text
    list_head = parse_list(child)
    if list_head:
        return list_head
    list_item = parse_list_item(child)
    if list_item:
        return list_item
    image = parse_image(child)
    if image:
        return image
    quote = parse_quotes(child)
    if quote:
        return quote
    link = parse_link(child)
    if link:
        return link
    twit = parse_tweet(child)
    if twit:
        return twit
    script = parse_script(child)
    if script:
        return script
    ig = parse_instagram_embed(child)
    if ig:
        return ig
    mention = parse_mention(child)
    if mention:
        return mention
    child_text = parse_children_in_node(child)
    if child_text:
        return child_text
    # print('++++++++Non parsed child: ' + str(child))
    return str(child)


def parse_children_in_node(child):
    child_text = ''
    for sub_child in child.children:
        if type(sub_child) is Tag:
            child_text += parseHTMLnode(sub_child)
        else:
            child_text += sub_child
    return child_text


def parse_list(child):
    if child.name == 'ul' or child.name == 'ol':
        ordered = '=1' if child.name[0] == 'o' else ''
        inner_text = parse_children_in_node(child)
        return '[LIST{}]{}[/LIST]'.format(ordered, inner_text)
    return ''


def parse_list_item(child):
    if child.name == 'li':
        inner_text = parse_children_in_node(child)
        return '[*]' + inner_text
    return ''


def parse_formatted_text(child):
    opening_tag = ''
    if child.name == 'i':
        opening_tag = 'I'
    if child.name == 'b' or child.name == 'strong':
        opening_tag = 'B'
    if child.name == 'font':
        opening_tag = 'SIZE={}'.format(child.attrs.get('size', ''))
    if opening_tag:
        inner_text = parse_children_in_node(child)
        return '[{}]{}[/{}]'.format(opening_tag, inner_text, opening_tag)
    return ''


def parse_script(child):
    if child.name == 'script':
        m = regex_youtube_script.search(child.text)
        if m:
            return '[YOUTUBE]{}[/YOUTUBE]'.format(m.group(1))
    else:
        script = child.select_one('script')
        if script:
            m = regex_youtube_script.search(script.text)
            if m:
                return '[YOUTUBE]{}[/YOUTUBE]'.format(m.group(1))
            pass
    return ''


def parse_instagram_embed(child):
    if child.name == 'blockquote' and ('instagram-media' in child.attrs.get('class', [])):
        ig_link = child.attrs.get('data-instgrm-permalink', '')
        if ig_link:
            m = regex_instagram_permalink.search(ig_link)
            if m:
                return '[IG]{}[/IG]'.format(m.group(1))
    return ''


def parse_image(child):
    if child.name == 'img':
        if 'imgpost' in child.attrs.get('class', []):
            return '[IMG]{}[/IMG]'.format(child.attrs.get('src', ''))
        elif 'inlineimg' in child.attrs.get('class', []):
            # emoticon
            return ':{}:'.format(child.attrs.get('title', ''))
    return ''


def parse_quotes(child):
    user_quoted = child.select_one('div > table > tr > td.alt2 > div:nth-child(1) > b')
    post_quoted = child.select_one('div > table > tr > td.alt2 > div:nth-child(1) > a')
    text_quoted = child.select_one('div > table > tr > td.alt2')
    if text_quoted:
        username = user_quoted.text if user_quoted else ''
        post_id = ''
        if post_quoted:
            m = regex_quote_user.search(post_quoted.attrs.get('href', ''))
            post_id = m.group(1) if m else ''
        if post_quoted or user_quoted:
            quote_div = child.select_one('div > table > tr > td.alt2 > div:nth-child(1)')
            quote_div.extract()
            text_quoted = child.select_one('div > table > tr > td.alt2 > div')
        inner_text = parse_children_in_node(text_quoted)
        return '[QUOTE={};{}]{}[/QUOTE]'.format(username, post_id, inner_text)
    return ''


def parse_link(child):
    if child.name == 'a':
        return '[URL="{}"]{}[/URL]'.format(child.get('href', ''), child.text)
    return ''


def parse_mention(child):
    if child.name == 'b' and ((type(child.previous) is NavigableString) and (child.previous.find('@') != -1)):
        if child.next and child.next.name == 'a':
            m = regex_mention_user.search(child.next.attrs.get('href', ''))
            if m:
                # mention = @[URL="https://xxx.com/foro/member.php?u=xxx"]xxx[/URL]
                return '[B][URL="{}"]{}[/URL][/B]'.format(child.next.get('href', ''), child.text)
    return ''


def parse_tweet(child):
    twit_messages = ''
    if child.name == 'blockquote' and ('twitter-tweet' in child.attrs.get('class', [])):
        twit_messages += '[TWEET]{}[/TWEET]\n'.format(child.text)
    tweets = child.select('blockquote.twitter-tweet')
    for twit in tweets:
        twit_messages += '[TWEET]{}[/TWEET]\n'.format(twit.text)
    return twit_messages
