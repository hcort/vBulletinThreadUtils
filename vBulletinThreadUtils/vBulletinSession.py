import configparser
import os

from vBulletinThreadUtils.vBulletinLoginSelenium import VBulletinLogin, create_session_object


class VBulletinSession:
    def __init__(self):
        self.__session = None
        # TODO https://docs.python.org/3/library/configparser.html
        self.__config = configparser.ConfigParser()
        self.__config['VBULLETIN'] = {}
        self.__config['SEARCHTHREADS'] = {}
        self.__config['DEFAULT'] = {
            'resources': os.path.join(os.getcwd(), 'resources'),
            'output_dir': os.path.join(os.getcwd(), 'output'),
            'output_format': 'HTML'
        }
        config_path = os.path.join(self.__config['DEFAULT']['resources'], 'config.ini')
        try:
            self.__config.read(config_path, encoding='utf-8')
        except IOError as err:
            print(f'Error opening config file: {config_path}')
        self.__output_dir = self.__config['VBULLETIN']['output_dir']
        self.__output_format = self.__config['VBULLETIN']['output_format']
        self.__user_name = self.__config['VBULLETIN'].get('logname', '')
        self.__password = self.__config['VBULLETIN'].get('password', '')
        self.__base_url = self.__config['VBULLETIN'].get('base_url', '')
        self.__search = dict(search_words=self.__config['SEARCHTHREADS'].get('search_words', ''),
                             search_in_title=self.__config['SEARCHTHREADS'].get('search_in_title', False),
                             search_user=self.__config['SEARCHTHREADS'].get('search_user', ''),
                             exact_user_name=self.__config['SEARCHTHREADS'].get('exact_user_name', False),
                             user_threads=self.__config['SEARCHTHREADS'].get('user_threads', False),
                             subforum_id=self.__config['SEARCHTHREADS'].get('subforum_id', ''),
                             subforum_recursive=self.__config['SEARCHTHREADS'].get('subforum_recursive', True),
                             date_select=self.__config['SEARCHTHREADS'].get('date_select', ''),
                             date_newer=self.__config['SEARCHTHREADS'].get('date_newer', True),
                             order_result_select=self.__config['SEARCHTHREADS'].get('order_result_select', ''),
                             order_descent=self.__config['SEARCHTHREADS'].get('order_descent', True),
                             show_as_threads=self.__config['SEARCHTHREADS'].get('show_as_threads', True),
                             strict_search=self.__config['SEARCHTHREADS'].get('strict_search', False),
                             minimum_posts=self.__config['SEARCHTHREADS'].get('minimum_posts', ''))

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

    # search parameters
    @property
    def search_words(self):
        return self.__search['search_words']

    @property
    def search_in_title(self):
        return self.__search['search_in_title']

    @property
    def search_user(self):
        return self.__search['search_user']

    @property
    def exact_user_name(self):
        return self.__search['exact_user_name']

    @property
    def user_threads(self):
        return self.__search['user_threads']

    @property
    def subforum_id(self):
        return self.__search['subforum_id']

    @property
    def subforum_recursive(self):
        return self.__search['subforum_recursive']

    @property
    def date_select(self):
        return self.__search['date_select']

    @property
    def date_newer(self):
        return self.__search['date_newer']

    @property
    def order_result_select(self):
        return self.__search['order_result_select']

    @property
    def order_descent(self):
        return self.__search['order_descent']

    @property
    def show_as_threads(self):
        return self.__search['show_as_threads']

    @property
    def strict_search(self):
        return self.__search['strict_search']

    @property
    def minimum_posts(self):
        return self.__search['minimum_posts']
    
    @search_words.setter
    def search_words(self, search_words):
        self.__search['search_words'] = search_words
        
    @search_in_title.setter
    def search_in_title(self, search_in_title):
        self.__search['search_in_title'] = search_in_title
        
    @search_user.setter
    def search_user(self, search_user):
        self.__search['search_user'] = search_user
        
    @exact_user_name.setter
    def exact_user_name(self, exact_user_name):
        self.__search['exact_user_name'] = exact_user_name
        
    @user_threads.setter
    def user_threads(self, user_threads):
        self.__search['user_threads'] = user_threads
        
    @subforum_id.setter
    def subforum_id(self, subforum_id):
        self.__search['subforum_id'] = subforum_id
        
    @subforum_recursive.setter
    def subforum_recursive(self, subforum_recursive):
        self.__search['subforum_recursive'] = subforum_recursive
        
    @date_select.setter
    def date_select(self, date_select):
        self.__search['date_select'] = date_select
        
    @date_newer.setter
    def date_newer(self, date_newer):
        self.__search['date_newer'] = date_newer
        
    @order_result_select.setter
    def order_result_select(self, order_result_select):
        self.__search['order_result_select'] = order_result_select
        
    @order_descent.setter
    def order_descent(self, order_descent):
        self.__search['order_descent'] = order_descent
        
    @show_as_threads.setter
    def show_as_threads(self, show_as_threads):
        self.__search['show_as_threads'] = show_as_threads
        
    @strict_search.setter
    def strict_search(self, strict_search):
        self.__search['strict_search'] = strict_search

    @minimum_posts.setter
    def minimum_posts(self, minimum_posts):
        self.__search['minimum_posts'] = minimum_posts

    def update_search_dict(self, search_params: dict):
        # i don't assign so I have a dictionary with all the default entries
        # in case search_params is missing something
        for item in search_params:
            self.__search[item] = search_params[item]

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

    @property
    def http_server_root(self):
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
        self.__session = VBulletinLogin(self.__base_url + 'misc.php?do=page&template=ident', login_data)


vbulletin_session = VBulletinSession()
