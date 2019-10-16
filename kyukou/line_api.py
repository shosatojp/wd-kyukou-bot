
from bson.objectid import ObjectId
import requests
import hmac
import hashlib
import base64
import time
isinpackage = not __name__ in ['line_api', '__main__']
if isinpackage:
    from . import line
    from .settings import settings
    from .db import get_collection
    from .util import Just, Curry
    from .log import log
else:
    from settings import settings
    from db import get_collection
    from util import Just, Curry
    from log import log
    import line

users_db = get_collection('users')


def validate(environ, body):
    if "HTTP_X_LINE_SIGNATURE" in environ:
        xsignature = environ["HTTP_X_LINE_SIGNATURE"].encode('utf-8')
        channel_secret = settings.line.channel_secret().encode('utf-8')
        digest = hmac.new(channel_secret, body, hashlib.sha256).digest()
        base64_digest = base64.b64encode(digest)
        return xsignature == base64_digest
    else:
        return False


def register(_user_id, _reply_token, realid=None):
    profile = get_profile(_user_id)
    default_notify = settings.default_notify()
    default_notify.update({'dest': 'line'})
    data = {
        "user_id": _user_id,
        "reply_token": _reply_token,
        "follow_time": time.time(),
        "display_name": profile["displayName"],
        "picture_url": profile["pictureUrl"],
        "status_message": profile.get('statusMessage')
    }
    if realid:  # 連携追加
        users_db.update_one({'_id': ObjectId(realid)}, {
            '$set': {
                'connections.line': data
            },
            'notifies': [default_notify]
        })
    elif users_db.find_one({'connections.line.user_id': _user_id}):  # データ上書き(再フォロー)
        users_db.update_one({'connections.line.user_id': _user_id}, {
            '$set': {
                'connections.line': data
            }
        })
    else:  # 新規登録
        users_db.insert_one({
            "connections": {
                "line": data,
            },
            "notifies": [default_notify]
        })


def parse(o):
    for event in o["events"]:
        event = Just(event)
        _type = event.type()
        _user_id = event.source.userId()
        if _user_id=='Udeadbeefdeadbeefdeadbeefdeadbeef':# LINE Developersの導通確認
            return
        if _type == 'follow':
            _reply_token = event.replyToken()
            register(_user_id, _reply_token)
            line.follow(_user_id)
        elif _type == 'unfollow':
            line.unfollow(_user_id)
        elif _type == 'message':
            _msg_type = event.message.type()
            if _msg_type == 'text':
                _reply_token = event.replyToken()
                _msg_text = event.message.text()
                if not users_db.find_one({"connections.line.user_id": _user_id}):
                    register(_user_id, _reply_token)
                users_db.update_one({"connections.line.user_id": _user_id}, {
                    "$set": {
                        "connections.line.reply_token": _reply_token,
                        "connections.line.last_message_time": time.time(),
                    }
                })
                line.message(_user_id, _msg_text)
            else:
                pass
        else:
            pass

def reply(user_id, msg_texts):
    data = users_db.find_one({"connections.line.user_id": user_id})["connections"]["line"]
    if data:
        url = 'https://api.line.me/v2/bot/message/reply'
        res = requests.post(url, json={
            "replyToken": data["reply_token"],
            "messages": [{"type": "text", "text": text}for text in msg_texts]
        }, headers={
            'content-type': 'application/json',
            'authorization': f'Bearer {settings.line.access_token()}'
        })
        return res.status_code
    else:
        raise RuntimeError


def push(user_id, msg_texts):
    '''
    # `push()`
    これは金がかかるのであまり使わないように！！
    '''
    data = users_db.find_one({"connections.line.user_id": user_id})["connections"]["line"]
    if data:
        url = 'https://api.line.me/v2/bot/message/push'
        res = requests.post(url, json={
            "to": user_id,
            "messages": [{"type": "text", "text": text}for text in msg_texts]
        }, headers={
            'content-type': 'application/json',
            'authorization': f'Bearer {settings.line.access_token()}'
        })
        return res.status_code
    else:
        raise RuntimeError


def broadcast(msg_texts):
    url = 'https://api.line.me/v2/bot/message/broadcast'
    res = requests.post(url, json={
        "messages": [{"type": "text", "text": text}for text in msg_texts]
    }, headers={
        'content-type': 'application/json',
        'authorization': f'Bearer {settings.line.access_token()}'
    })
    return res.status_code


def multicast(user_ids, msg_texts):
    url = 'https://api.line.me/v2/bot/message/multicast'
    res = requests.post(url, json={
        "to": user_ids,
        "messages": [{"type": "text", "text": text}for text in msg_texts]
    }, headers={
        'content-type': 'application/json',
        'authorization': f'Bearer {settings.line.access_token()}'
    })
    return res.status_code


def get_profile(user_id):
    url = f'https://api.line.me/v2/bot/profile/{user_id}'
    res = requests.get(url, headers={
        'authorization': f'Bearer {settings.line.access_token()}'
    })
    return res.json()


def get_real_user_id(user_id):
    return Just(users_db.find_one({"connections.line.user_id": user_id}))._id[lambda e:None if e == None else str(e)]()


def get_line_user_id(real_user_id):
    data = Just(users_db.find_one({"_id": ObjectId(real_user_id)}))
    if data() and 'line' in data.connections():
        return data.connections.line.user_id()
    else:
        raise RuntimeError
