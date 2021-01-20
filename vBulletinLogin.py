import requests


def VBulletinLogin(login_url='', login_data={}):
    if not login_url:
        return None
    session = requests.Session()
    r = session.post(login_url, data=login_data)
    cookie_bbimloggedin = r.cookies.get('bbimloggedin', default='no')
    if cookie_bbimloggedin == 'yes':
        return session
    return None
