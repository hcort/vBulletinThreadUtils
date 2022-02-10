import requests

from vBulletinLoginSelenium import VBulletinLoginSelenium


def VBulletinLogin(login_url='', login_data={}):
    return VBulletinLoginSelenium(login_url=login_url, login_data=login_data)


def VBulletinLoginRequests(login_url='', login_data={}):
    # FIXME error 403 ->
    # https://www.forocoches.com/foro/showthread.php?t=8570466&highlight=bot
    # https://github.com/verlsk/pole_bot_fc/blob/main/main.py
    if not login_url:
        return None
    session = requests.Session()
    user_agent = {'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0'}
    r = session.post(login_url, data=login_data, headers=user_agent)
    if r.status_code != requests.codes.ok:
        print('Login post failed with error {error_code}'.format(error_code=r.status_code))
    cookie_bbimloggedin = r.cookies.get('bbimloggedin', default='no')
    if cookie_bbimloggedin == 'yes':
        return session
    print('Login post failed, cookie not found')
    return None
