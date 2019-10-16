from datetime import datetime
import time
import json
import base64
import requests
import urllib
from bson.objectid import ObjectId
isinpackage = not __name__ in ['line_notify_api', '__main__']
if isinpackage:
    from .settings import settings
    from . import util
    from .util import Just
    from .db import get_collection
    from .import certificate
    from . import line_api
else:
    import util
    import certificate
    from settings import settings
    from util import Just
    from db import get_collection
    import line_api

users_db = get_collection('users')


def get_redirect_link(realid):
    state = util.generate_id(50)
    certificate.register_state(state, "line_notify_oauth", {"realid": realid})
    return 'https://notify-bot.line.me/oauth/authorize?' + \
        'response_type=code&' +\
        f'client_id={settings.line_notify.client_id()}&' +\
        f'redirect_uri={settings.url_prefix()}{settings.line_notify.redirect_uri()}&' +\
        'scope=notify&' +\
        f'state={state}'


def code_to_access_token(code):
    endpoint = 'https://notify-bot.line.me/oauth/token'
    res = requests.post(endpoint, params={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.url_prefix()+settings.line_notify.redirect_uri(),
        'client_id': settings.line_notify.client_id(),
        'client_secret': settings.line_notify.client_secret(),
    })
    return res.status_code == 200 and res.json()


def append(realid, tokens):
    tokens.update({
        'follow_time': time.time()
    })
    user = users_db.find_one({'_id': ObjectId(realid)})
    users_db.update_one({'_id': ObjectId(realid)}, {
        '$set': {
            'connections.line_notify': tokens,
        },
        '$inc': {
            'connections.length': 0 if Just(user).connections.line_notify() else 1
        }
    })


def get_access_token(realid):
    return Just(users_db.find_one({'_id': ObjectId(realid)})).connections.line_notify.access_token()


def has_account(realid):
    return not not get_access_token(realid)


def send(realid, message):
    '''
    # `send()`
    1000回/ユーザー時 まで
    '''
    res = requests.post('https://notify-api.line.me/api/notify', headers={
        'Authorization': f'Bearer {get_access_token(realid)}'
    }, params={"message":  message})
    return res.status_code == 200
