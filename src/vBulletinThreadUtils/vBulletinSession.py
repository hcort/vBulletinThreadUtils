"""
    Encapsulates all the data needed to parse threads in a vBulletin forum

    It also serves as an access point for the selenium webdriver
"""
import configparser
import os

from .vBulletinLoginSelenium import create_session_object, create_driver_and_login, hijack_cookies


class VBulletinSession:
    """
        The class that encapsulates the data
        It reads from a config.ini file
    """
    def __init__(self):
        self.__session = None
        # TODO https://docs.python.org/3/library/configparser.html
        self.__config = configparser.ConfigParser()
        self.__config['VBULLETIN'] = {}
        self.__config['DEFAULT'] = {
            'resources': os.path.join(os.getcwd(), 'resources'),
            'output_dir': os.path.join(os.getcwd(), 'output'),
            'output_format': 'HTML'
        }
        config_path = os.path.join(self.__config['DEFAULT']['resources'], 'config.ini')
        try:
            self.__config.read(config_path, encoding='utf-8')
        except IOError as err:
            print(f'Error opening config file: {config_path} - {err}')
        self.__output_dir = self.__config['VBULLETIN']['output_dir']
        self.__user_name = self.__config['VBULLETIN'].get('logname', '')
        self.__password = self.__config['VBULLETIN'].get('password', '')
        self.__base_url = self.__config['VBULLETIN'].get('base_url', '')
        self.__driver = None

    def __del__(self):
        if self.__driver:
            self.__driver.close()

    @property
    def session(self):
        if not self.__session:
            self.__do_login()
        return self.__session

    @property
    def config(self):
        return self.__config

    @property
    def output_dir(self):
        return self.__output_dir

    @output_dir.setter
    def output_dir(self, output_dir):
        self.__output_dir = output_dir

    def session_restart(self):
        a_session = create_session_object()
        for name, value in self.__session.cookies.items():
            a_session.cookies.update({name: value})
        self.__session.close()
        self.__session = a_session

    @property
    def user_name(self):
        return self.__user_name

    @user_name.setter
    def user_name(self, user_name):
        self.__user_name = user_name

    @property
    def password(self):
        return self.__password

    @password.setter
    def password(self, password):
        self.__password = password

    @property
    def base_url(self):
        return self.__base_url

    @base_url.setter
    def base_url(self, base_url):
        self.__base_url = base_url

    def __do_login(self):
        if not self.__user_name or not self.__password:
            print('Missing config entries: login data')
            return
        if not self.__base_url:
            print('Missing config entries: base URL')
            return
        # This is the form data that the page sends when logging in
        login_data = {
            'vb_login_username': self.__user_name,
            'vb_login_password': self.__password}
        # .../foro/misc.php?do=page&template=ident
        # self.__session = VBulletinLogin(self.__base_url + 'misc.php?do=page&template=ident', login_data)
        self.__driver = create_driver_and_login(
            login_url=f'{self.__base_url}misc.php?do=page&template=ident', login_data=login_data)
        self.__session = hijack_cookies(self.__driver)
        cookie_bbimloggedin = self.__session.cookies.get('bbimloggedin', default='no')
        if cookie_bbimloggedin == 'no':
            print('cookie bbimloggedin no encontrada')

    @property
    def driver(self):
        if not self.__driver:
            if not self.__user_name or not self.__password:
                print('Missing config entries: login data')
                return
            if not self.__base_url:
                print('Missing config entries: base URL')
                return
            # This is the form data that the page sends when logging in
            login_data = {
                'vb_login_username': self.__user_name,
                'vb_login_password': self.__password}
            # .../foro/misc.php?do=page&template=ident
            self.__driver = vBulletinLoginSelenium.create_driver_and_login(
                login_url=f'{self.__base_url}misc.php?do=page&template=ident', login_data=login_data)
        return self.__driver


vbulletin_session = VBulletinSession()
