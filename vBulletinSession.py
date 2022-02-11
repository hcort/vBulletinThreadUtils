import configparser
import os

from vBulletinLogin import VBulletinLogin


class VBulletinSession:
    def __init__(self):
        self.__session = None
        # TODO https://docs.python.org/3/library/configparser.html
        self.__config = configparser.ConfigParser()
        self.__config.read(os.path.join('resources', 'config.ini'), encoding='utf-8')

    @property
    def session(self):
        if not self.__session:
            self.__do_login()
        return self.__session

    @property
    def config(self):
        return self.__config

    def __do_login(self):
        try:
            # TODO username and pwd may not be needed in public threads
            username = self.__config['VBULLETIN']['logname']
            pwd = self.__config['VBULLETIN']['password']
            base_url = self.__config['VBULLETIN']['base_url']
        except KeyError as err:
            print('Missing config entries: ' + str(err))
            return
        # This is the form data that the page sends when logging in
        login_data = {
            'do': 'login',
            'forceredirect': '0',
            'url': '',
            'vb_login_md5password': '',
            'vb_login_md5password_utf': '',
            's': 'f6a6b3226a64c319a11efd886f798259',
            'securitytoken': 'guest',
            'vb_login_username': username,
            'vb_login_password': pwd,
            'cookieuser': '1',
            'logb2': 'Acceder'}
        # FIXME retrasar la creación de la sesión hasta el último momento
        # login_url = 'https://www.forocoches.com/foro/misc.php?do=page&template=ident'
        self.__session = VBulletinLogin(base_url + 'login.php', login_data)


vbulletin_session = VBulletinSession()
