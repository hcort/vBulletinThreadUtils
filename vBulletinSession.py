import configparser
import os

from vBulletinLoginSelenium import VBulletinLogin, create_session_object


class VBulletinSession:
    def __init__(self):
        self.__session = None
        # TODO https://docs.python.org/3/library/configparser.html
        self.__config = configparser.ConfigParser()
        self.__config.read(os.path.join('resources', 'config.ini'), encoding='utf-8')
        # some optional configuration values
        self.__output_dir = self.__config['VBULLETIN'].get('output_dir', '')
        self.__output_format = self.__config['VBULLETIN'].get('output_format', 'HTML')

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

    @property
    def output_format(self):
        return self.__output_format

    @output_format.setter
    def output_format(self, output_format):
        self.__output_format = output_format

    def session_restart(self):
        a_session = create_session_object()
        for name, value in self.__session.cookies.items():
            a_session.cookies.update({name: value})
        self.__session.close()
        self.__session = a_session

    def __do_login(self):
        try:
            username = self.__config['VBULLETIN']['logname']
            pwd = self.__config['VBULLETIN']['password']
            base_url = self.__config['VBULLETIN']['base_url']
        except KeyError as err:
            print('Missing config entries: ' + str(err))
            return
        # This is the form data that the page sends when logging in
        login_data = {
            'vb_login_username': username,
            'vb_login_password': pwd}
        self.__session = VBulletinLogin(base_url + 'login.php', login_data)


vbulletin_session = VBulletinSession()
