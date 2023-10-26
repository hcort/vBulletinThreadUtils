"""
    Several utilities used across the module

"""
import datetime
from re import Pattern
from time import altzone
import requests
from bs4 import BeautifulSoup

from vBulletinThreadUtils.vBulletinSession import vbulletin_session


def get_soup_requests(url: str = None) -> BeautifulSoup | None:
    if not url:
        return None
    current_page = vbulletin_session.session.get(url, timeout=30)
    if current_page.status_code != requests.codes.ok:
        print(f'Error getting {url} - response code: {current_page.status_code}')
        return None
    return BeautifulSoup(current_page.text, features="html.parser")


def get_string_from_regex(pattern: Pattern, text: str) -> str:
    """

    :param pattern:
    :param text:
    :return: the text that matches the pattern or empty string
    """
    m = pattern.search(text)
    return m.group(1) if m else ''


def normalize_date_string(date_string):
    """

    :param date_string: format = '2017-07-21T16:17:16+00:00'
    :return: format = aaaa-mm-dd - hh:mm with hours and minutes corrected from UTC
    """
    parsed_time = datetime.datetime.strptime(date_string[:-6], '%Y-%m-%dT%H:%M:%S')
    diff_hour = altzone / 3600
    offset_time = parsed_time - datetime.timedelta(hours=diff_hour)
    return offset_time.strftime('%Y-%m-%d - %H:%M')


month_replacement_number = {'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'may': '05', 'jun': '06',
                            'jul': '07', 'ago': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'}


def normalize_date_string_vbulletin_format(vbulletin_date, hour_minutes):
    """

    :param hour_minutes: format = 'hh:mm'
    :param vbulletin_date: 'dd-mmm-aaaa' / 'Hoy' / 'Ayer'
        mmm are months in spanish
    :return: format = aaaa-mm-dd - hh:mm
    """
    if vbulletin_date[0] == 'H':
        return f"{datetime.date.today().strftime('%Y-%m-%d')} - {hour_minutes}"
    if vbulletin_date[0] == 'A':
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        return f"{yesterday.strftime('%Y-%m-%d')} - {hour_minutes}"
    month_num = month_replacement_number[vbulletin_date[3:6]]
    return datetime.datetime.strptime(
        f"{vbulletin_date.replace(vbulletin_date[3:6], month_num)} - {hour_minutes}", '%d-%m-%Y - %H:%M'
    ).strftime('%Y-%m-%d - %H:%M')
