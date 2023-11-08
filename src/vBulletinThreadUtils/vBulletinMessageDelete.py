"""
    This will be done using Selenium

    This method navigates to a specific message (via it own URL) and then click
    the buttons for deletion
"""
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

regex_message_id = re.compile(r'#post([0-9]+)')


def delete_message(driver, message):
    """

    :param driver:
    :param message: The url for the specific message
    :return:
    """
    m = regex_message_id.search(message)
    message_id = m.group(1) if m else ''
    if not message_id:
        return
    timeout = 5
    try:
        driver.get(message)
        element = driver.find_element(By.NAME, f'vB::QuickEdit::{message_id}')
        element.click()
        element_present = EC.presence_of_element_located((By.ID, 'vB_Editor_QE_1_delete'))
        WebDriverWait(driver, timeout).until(element_present)
        element = driver.find_element(By.ID, 'vB_Editor_QE_1_delete')
        element.click()
        element_present = EC.presence_of_element_located((By.ID, 'rb_del_soft'))
        WebDriverWait(driver, timeout).until(element_present)
        element = driver.find_element(By.ID, 'rb_del_soft')
        element.click()
        element = driver.find_element(By.ID, 'quickedit_dodelete')
        element.click()
        # element_present = EC.presence_of_element_located((By.ID, f'post_message_{message_id}'))
        # WebDriverWait(driver, timeout).until_not(element_present)
    except Exception as ex:
        print(f'Error deleting {message}: {str(ex)}')
