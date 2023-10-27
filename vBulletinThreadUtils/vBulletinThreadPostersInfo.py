"""
    A call to the whoposted method that retrieves the posters in a thread and number of messages from each of them


    base_url/misc.php?do=whoposted&t=thread_id

    The posters are in a table with odd and even rows
"""
from selenium.webdriver.common.by import By

from vBulletinThreadUtils.vBulletinSession import vbulletin_session

odd_row_user_css = 'table.tborder>tbody>tr>td.alt1:nth-child(1)'
odd_row_messages_css = 'table.tborder>tbody>tr>td.alt1:nth-child(2)'
even_row_user_css = 'table.tborder>tbody>tr>td.alt2:nth-child(1)'
even_row_messages_css = 'table.tborder>tbody>tr>td.alt2:nth-child(2)'


def get_posters_from_thread(thread_id):
    driver = vbulletin_session.driver
    who_posted_url = f'{vbulletin_session.base_url}/misc.php?do=whoposted&t={thread_id}'
    driver.get(who_posted_url)
    odd_rows = list(zip([x.text for x in driver.find_elements(By.CSS_SELECTOR, odd_row_user_css)],
                        [x.text for x in driver.find_elements(By.CSS_SELECTOR, odd_row_messages_css)]))
    even_rows = list(zip([x.text for x in driver.find_elements(By.CSS_SELECTOR, even_row_user_css)],
                         [x.text for x in driver.find_elements(By.CSS_SELECTOR, even_row_messages_css)]))
    posters = {}
    for odd, even in zip(odd_rows, even_rows):
        if odd:
            posters[odd[0]] = odd[1]
        if even:
            posters[even[0]] = even[1]
    return posters
