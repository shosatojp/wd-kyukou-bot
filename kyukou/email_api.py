from bson.objectid import ObjectId
from email.mime.text import MIMEText
import smtplib
import requests
import time
import hashlib
isinpackage = not __name__ in ['email_api', '__main__']

if isinpackage:
    from . import certificate
    from .settings import settings
    from .db import get_collection
else:
    # import certificate
    from settings import settings
    from db import get_collection

users_db = get_collection('users')


def register(o={
    'email_addr': '',
    'password': '',
    'name': '',
    'referrer': 'line|web'
}):
    if "email_addr" in o and not users_db.find_one({"connections.email.email_addr": o["email_addr"], "connections.email.validated": True}):
        password_hash = hashlib.sha256((o["password"]+settings["hash_salt"] or '').encode()).hexdigest()
        users_db.insert_one({
            "connections": {
                "email": {
                    "email_addr": o["email_addr"],
                    "name": o["name"],
                    "password_hash": password_hash,
                    "varidated": False,
                    "referrer": o['referrer']
                }
            },
            "length": 1
        })
        return True
    else:
        return False


def append(o={
    'email_addr': '',
    'real_user_id': '',
    'referrer': '',
}):
    users_db.update_one({'_id': ObjectId(o['real_user_id'])}, {
        '$set': {
            'connections.email': {
                'email_addr': o['email_addr'],
                'referrer': o['referrer'],
                'verified': True
            }
        },
        '$inc': {
            'connections.length': 1
        }
    })


def send_mails(msgs):
    server = smtplib.SMTP(settings["email"]["smtp_server"], settings["email"]["smtp_port"])
    server.login(settings["email"]["from_addr"], settings["email"]["password"])
    for msg in msgs:
        server.send_message(msg)
    server.quit()


def make_message(to_addr, subject, content):
    msg = MIMEText(content, "html")
    msg["Subject"] = subject
    msg["To"] = to_addr
    msg["From"] = settings["email"]["from_addr"]
    return msg


if not isinpackage:
    msg = make_message('kyukou@monoid.app', 'title', 'content')
    send_mails([msg])
