from . import parse_share
import base64
import json
import hmac
import hashlib
from . import certificate
import re
import urllib
from .route import *
from pprint import pprint
from . import line_api
from . import email_api
from . import google_api
from . import line_notify_api
from . import twitter_api
from . import util
from .settings import settings
from .log import log
import os
import sys
from .log import log
# 上から順に優先

LINE_API_NETWORKS = ['0.0.0.0/0']
TWITTER_API_NETWORKS = ['0.0.0.0/0','199.59.148.0/22', '199.16.156.0/22']
LOCAL_NETWORKS = ['192.168.0.0/16']

# LINE botからイベントがあったときに来る
@route('post', '/api/v1/line/webhook', networks=LINE_API_NETWORKS)
def line_webhook(environ):
    body = get_body(environ)
    o = body_to_json(body)
    if line_api.validate(environ, body):
        line_api.parse(o)
        return status(200)
    else:
        return status(403)


@route('get', '/api/v1/line/notify/redirect_link')
def line_notify_redirect_link(environ):
    realid = get_query(environ).get('realid')
    if realid:
        return redirect(line_notify_api.get_redirect_link(realid))
    else:
        return status(400)


@route('get', '/api/v1/line/notify')
def line_notify(environ):
    q = get_query(environ)
    data = certificate.validate_state(q['state'], 'line_notify_oauth')
    if data:
        tokens = line_notify_api.code_to_access_token(q['code'])
        if tokens:
            line_notify_api.append(data['realid'], tokens)
            line_notify_api.send(data['realid'], '連携が完了しました！')
            line_notify_api.send(data['realid'], 'こちらで休講情報の配信をいたします')
            return redirect('/')
    return redirect('/#/expired')

# Twitter Get Redirect URL to Allow Connection
@route('get', '/api/v1/twitter/redirect_url')
def twitter_redirect_url(environ):
    q = get_query(environ)
    if q.get('consumer_key_secret') == settings.twitter.consumer_key_secret()\
            and q.get('consumer_key') == settings.twitter.consumer_key():
        url = twitter_api.get_redirect_url()
        return redirect(url)
    else:
        return status(400)

# Twitter Webhook
@route('post', '/api/v1/twitter/webhook')
def twitter_webhook(environ):
    x_signature = environ.get('HTTP_X_TWITTER_WEBHOOKS_SIGNATURE')
    body=get_body(environ)
    if x_signature and twitter_api.validate(x_signature, body):
        twitter_api.parse(body_to_json(body))
        return status(200)
    else:
        return status(400)

# Twitter Webhook CRC
@route('get', '/api/v1/twitter/webhook', networks=TWITTER_API_NETWORKS)
def twitter_webhook(environ):
    sha256_hash_digest = hmac.new(settings.twitter.consumer_key_secret().encode(),
                                  msg=get_query(environ)['crc_token'].encode(),
                                  digestmod=hashlib.sha256).digest()
    response = {
        'response_token': 'sha256=' + base64.b64encode(sha256_hash_digest).decode()
    }
    return json(response)

# Settings for Bot Account
@route('get', '/api/v1/twitter/callback', networks=LOCAL_NETWORKS)
def twitter_callback(environ):
    q = get_query(environ)
    access_tokens = twitter_api.get_access_token(q['oauth_token'], q['oauth_verifier'])
    if access_tokens:
        print('Access Tokenを取得しました', access_tokens)
        twitter_api.store_tokens(access_tokens)
        webhook = twitter_api.validate_webhook()
        if webhook.status_code == 200:
            print('Webhookの登録を完了しました')
            twitter_api.subscribe_user(webhook.json()['id'], access_tokens['oauth_token'], access_tokens['oauth_token_secret'])
            return text('Bot用アカウントの設定が完了しました')
        else:
            return text(webhook.text, 400)
    return status(400)


@route('get', '/api/v1/line/email')
def line_email_validation(environ):
    q = get_query(environ)
    data = certificate.validate_token('line_email', q.get('realid'), q.get('token'))
    if data:
        email_api.append({
            'email_addr': data['email_addr'],
            'real_user_id': q['realid'],
            'referrer': 'line'
        })
        return file('/c/validated')
    else:
        return status(400)


@route('head', '/api/v1/upload/validate')
def validate_upload_token(environ):
    realid, token = environ.get("HTTP_X_KYUKOU_REALID"), environ.get("HTTP_X_KYUKOU_TOKEN")
    if realid and token and certificate.validate_token('csv_upload', realid, token, expire=False):
        return status(200)
    else:
        return status(401)


@route('post', '/api/v1/upload')
def upload_csv(environ):
    realid, token = environ.get("HTTP_X_KYUKOU_REALID"), environ.get("HTTP_X_KYUKOU_TOKEN")
    cert = certificate.validate_token('csv_upload', realid, token)
    if realid and token and cert:
        try:
            csv = get_body(environ).decode('cp932')
            data = parse_share.parse_csv(csv)
        except Exception as e:
            log(__name__, e)
            return status(406)
        if data:
            parse_share.register(realid, data)
            if cert.get('referrer') == 'line':
                line_user_id = line_api.get_line_user_id(realid)
                line_api.push(line_user_id, [
                    'おめでとうございます！CSVファイルがアップロードされました！',
                    '休講情報を配信するためにLINE Notifyの連携をお願いします。これが最後のステップです',
                    line_notify_api.get_redirect_link(realid)
                ])
                return status(200)
            elif cert.get('referrer') == 'twitter':
                twitter_user_id = twitter_api.get_twitter_user_id(realid)
                if twitter_user_id:
                    twitter_api.send(twitter_user_id, 'おめでとうございます！CSVファイルがアップロードされました！')
                return status(200)
            return status(401)
        else:
            return status(406)
    else:
        return status(401)


@route('get', '/api/v1/oauth/google/redirect_link')
def google_oauth_start_auth(environ):
    return redirect(google_api.get_redirect_link())


@route('get', '/api/v1/oauth/google/redirect')
def google_oauth_redirect(environ):
    q = get_query(environ)
    data = certificate.validate_state(q['state'], 'google_oauth')
    if data:
        line_api.push(line_api.get_line_user_id(data['realid']), ['Thank you for your registration!', '[Notification]\nMath class was cancelled!!'])
        profile, tokens = google_api.code_to_refresh_token(q['code'])
        google_api.register(profile, tokens, data['realid'])
        import datetime
        start = datetime.datetime(2019, 10, 9, 13, 0, 0)
        end = start+datetime.timedelta(minutes=90)
        google_api.add_event(data['realid'], start.isoformat(), end.isoformat(), {'summary': 'Math class was cancelled!'})
        return redirect('/#/registerd')
    else:
        return redirect('/#/expired')


@route('post', '/api/v1/email/register')
def email(environ):
    if email_api.register(get_body_json(environ)):
        certificate.generate_token()
    return status(200)


# @route('post','/api/v1/slack/webhook')
# def slack_webhook(environ):
#     q=get_body_json(environ)
#     print(q)
#     return text(q.get('challenge'))
# @route('get', '/')
# def getfile(environ):
#     return file(environ["PATH_INFO"])


@route()
def fallback(environ):
    return redirect('/')
