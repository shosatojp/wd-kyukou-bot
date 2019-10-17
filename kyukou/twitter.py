from . import scheduler
from .log import log
from datetime import datetime
import traceback
import re
from . import notify
from . import util
from . import twitter_api
from .db import get_collection
from . import google_api
from . import certificate
from .util import Just
from . import email_api
from .settings import settings
from .procedure import *
from . import publish
from . import user_data
from . import copipe
from . import parse_share

csv_procedure = ProcedureDB(lambda user_id, msg_text, *args, **kwargs: msg_text == 'csv', 'twitter_csv', title='csv', description='履修登録のCSVファイルのアップロードリンクを取得します。')


@process(csv_procedure, 0)
def reply_csv_upload_link(user_id, msg_text, *args, **kwargs):
    real_user_id = twitter_api.get_real_user_id(user_id)
    token = certificate.generate_token(real_user_id, 'csv_upload', {'referrer': 'twitter'})
    link = f'{settings.url_prefix()}/c/uploadcsv/?token={token}&realid={real_user_id}'
    twitter_api.send(user_id, link)
    twitter_api.send(user_id, 'このリンクからCSVファイルをアップロードしてください。リンクの有効期限は1時間です。以前取得したリンクは無効化されます。')
    csv_procedure.set_progress(user_id, 0)


time_procedure = ProcedureDB(lambda user_id, msg_text, *args, **kwargs: msg_text == 'time', 'twitter_time', title='time', description='休講の通知時間を設定します。')


@process(time_procedure, 0)
def validate_input(user_id, msg_text, *args, **kwargs):
    twitter_api.sends(user_id, ['通知の形式を選択し、対応する「数字」を入力してください。\n'
                                + '【 1 】休講情報を見つけたら即時通知する\n'
                                + '【 2 】休講日の何日前、何時間前など、通知時間を細かく設定する\n'
                                + '尚、この通知設定は複数追加できます。'])
    time_procedure.set_progress(user_id, 0)


@process(time_procedure, 1)
def validate_num(user_id, msg_text, *args, **kwargs):
    if msg_text == '1':
        realid = twitter_api.get_real_user_id(user_id)
        if notify.add_notify(realid, {'type': 'scraping', 'offset': 0, 'dest': 'twitter'}):
            publish.remove_queue(realid)
            twitter_api.sends(user_id, ['登録完了です。休講情報を見つけたらすぐ通知します。'])
        else:
            twitter_api.sends(user_id, ['通知が最大数10に達したか、すでに同じものがあるため追加できません'])
        time_procedure.set_progress(user_id, 3)
    elif msg_text == '2':
        twitter_api.sends(user_id, ['休講の何日前に通知しますか？\n当日の場合は【 0 】"、前日の場合は【 1 】、2日前の場合は【 2 】...のように入力してください。'])
        time_procedure.set_progress(user_id, 1)
    else:
        twitter_api.sends(user_id, ['数値の形式が間違っています。もう一度入力してください。'])
        time_procedure.set_progress(user_id, 0)


@process(time_procedure, 2)
def please_enter_time(user_id, msg_text, *args, **kwargs):
    m = re.match(r'^(\d{1,2})$', msg_text)
    if m:
        d = int(m.group(1))
        if 0 <= d <= 30:
            time_procedure.set_info(user_id, 'day', d)
            twitter_api.sends(user_id, ['その日の何時に通知しますか？\n"6:30"、"23:00"のように"時:分"となるよう24時間表記で送信してください。'])
            time_procedure.set_progress(user_id, 2)
            return
    twitter_api.sends(user_id, ['数値の形式が間違っています。もう一度入力してください。'])
    time_procedure.set_progress(user_id, 1)


@process(time_procedure, 3)
def validate_time(user_id, msg_text, *args, **kwargs):
    try:
        dayoffset = -time_procedure.get_info(user_id).get('day', 0)
        time_data = datetime.strptime(msg_text, '%H:%M')
        realid = twitter_api.get_real_user_id(user_id)
        if notify.add_notify(realid, {'type': 'day', 'offset': notify.day_hour_minute_to_day_offset(dayoffset, time_data.hour, time_data.minute), 'dest': 'twitter'}):
            publish.remove_queue(realid)
            twitter_api.sends(user_id, ['通知時間を登録しました。'])
        else:
            twitter_api.sends(user_id, ['通知が最大数10に達したか、すでに同じものがあるため追加できません'])
        time_procedure.set_progress(user_id, 3)
    except ValueError:
        twitter_api.sends(user_id, ['数値の形式が間違っています。もう一度入力してください'])
        time_procedure.set_progress(user_id, 2)
    except:
        log(__name__, traceback.format_exc(), 4)
        twitter_api.sends(user_id, ['不明なエラーが発生しました。申し訳ありませんが、最初からやり直してください。'])
        time_procedure.set_progress(user_id, 2)


google_oauth_procedure = ProcedureDB(lambda user_id, msg_text: msg_text == 'google', 'twitter_google')
@process(google_oauth_procedure, 0)
def redirect_to_google_auth(user_id, msg_text, *args, **kwargs):
    twitter_api.sends(user_id, [google_api.get_redirect_link(twitter_api.get_real_user_id(user_id))])


status_procedure = ProcedureDB(lambda user_id, msg_text, *args, **kwargs: msg_text == 'status', 'twitter_status', title='status', description='設定した休講の通知時間の一覧を表示します')


@process(status_procedure, 0)
def display_status(user_id, msg_text, *args, **kwargs):
    s = notify.format_notifies(twitter_api.get_real_user_id(user_id))
    if s:
        twitter_api.sends(user_id, ['通知の登録情報を表示します。', s])
    else:
        twitter_api.sends(user_id, ['通知は設定されていません', '【time】と入力して設定してください'])
    status_procedure.set_progress(user_id, 0)


delete_procedure = ProcedureDB(lambda user_id, msg_text, *args, **kwargs: msg_text == 'delete', 'twitter_delete', title='delete', description='設定した休講の通知時間を削除します')


@process(delete_procedure, 0)
def delete_status(user_id, msg_text, *args, **kwargs):
    s = notify.format_notifies(twitter_api.get_real_user_id(user_id))
    if s:
        twitter_api.sends(user_id, ['削除する番号を入力してください', s])
        delete_procedure.set_progress(user_id, 0)
    else:
        twitter_api.sends(user_id, ['通知は設定されていません'])
        delete_procedure.set_progress(user_id, 1)


@process(delete_procedure, 1)
def delete_notify(user_id, msg_text, *args, **kwargs):
    try:
        realid = twitter_api.get_real_user_id(user_id)
        if 1 <= int(msg_text) <= len(notify.get_notifies(realid)):
            notify.delete_notify(realid, int(msg_text))
            twitter_api.sends(user_id, ['削除しました'])
            delete_procedure.set_progress(user_id, 1)
        else:
            twitter_api.sends(user_id, ['正しく入力してください'])
            delete_procedure.set_progress(user_id, 0)
    except:
        twitter_api.sends(user_id, ['正しく入力してください'])
        delete_procedure.set_progress(user_id, 0)


request_procedure = ProcedureDB(lambda user_id, msg_text, *args, **kwargs: msg_text == 'request', 'twitter_request', title='request', description='運営に要望を送ることができます')


@process(request_procedure, 0)
def get_request(user_id, msg_text, *args, **kwargs):
    twitter_api.sends(user_id, ['このサービスに関して、何か要望があれば入力してください。やめるには【end】と入力します'])
    request_procedure.set_progress(user_id, 0)


@process(request_procedure, 1)
def send_request(user_id, msg_text, *args, **kwargs):
    msg = email_api.make_message(settings.admin_email_addr(), '【ご注文は休講情報ですか？】ユーザーからの問い合わせ', f'<h1>REAL_USER_ID={twitter_api.get_real_user_id(user_id)}, REF=TWITTER</h1><p>{msg_text}</p>')
    scheduler.pool.submit(email_api.send_mails, [msg])
    twitter_api.sends(user_id, ['ご協力ありがとうございました。'])
    request_procedure.set_progress(user_id, 1)


help_procedure = ProcedureDB(lambda user_id, msg_text, *args, **kwargs: msg_text == 'help', 'twitter_help', title='help', description='トークで使えるコマンドの一覧を表示します')


@process(help_procedure, 0)
def display_help(user_id, msg_text, *args, **kwargs):
    twitter_api.send(user_id, description)
    help_procedure.set_progress(user_id, 0)


cources_procedure = ProcedureDB(lambda user_id, msg_text, *args, **kwargs: msg_text == 'cources' or msg_text ==
                                'cource' or msg_text == 'list', 'twitter_cources', title='list', description='登録された履修科目の一覧を表示します')


@process(cources_procedure, 0)
def get_request(user_id, msg_text, *args, **kwargs):
    realid = twitter_api.get_real_user_id(user_id)
    cources = user_data.list_of_courses(realid)
    twitter_api.sends(user_id,  ['登録されている履修科目の一覧です', cources] if cources else ['登録されている履修科目はありません', '【csv】と入力して履修情報のアップロードリンクを取得してください'])
    cources_procedure.set_progress(user_id, 0)


copipe_procedure = ProcedureDB(lambda user_id, msg_text, *args, **kwargs: msg_text == 'copipe', 'twitter_copipe', title='copipe', description='履修登録画面の「曜日の行」からコピペして貼り付けても登録できます')


@process(copipe_procedure, 0)
def copipe0(user_id, msg_text, *args, **kwargs):
    realid = twitter_api.get_real_user_id(user_id)
    twitter_api.sends(user_id,  ['https://campusweb.office.uec.ac.jp/campusweb/ ここから講義情報の部分を「曜日の行付近から」コピペしてください'])
    copipe_procedure.set_progress(user_id, 0)


@process(copipe_procedure, 1)
def copipe1(user_id, msg_text, *args, **kwargs):
    realid = twitter_api.get_real_user_id(user_id)
    data = copipe.load(kwargs['raw'])
    if data:
        copipe_procedure.set_info(user_id, 'copipe_data', data)
        twitter_api.sends(user_id,  [f'登録する講義はこちらでよろしいですか？', user_data.format_courses(data), 'OKなら【 y 】、コピペし直すなら【 n 】を入力してください'])
        copipe_procedure.set_progress(user_id, 1)
    else:
        twitter_api.sends(user_id, ['正常に読み取れませんでした。もう一度「曜日の行付近から」貼り付けてください'])
        copipe_procedure.set_progress(user_id, 0)


@process(copipe_procedure, 2)
def copipe2(user_id, msg_text, *args, **kwargs):
    realid = twitter_api.get_real_user_id(user_id)
    if msg_text == 'y':
        data = copipe_procedure.get_info(user_id).get('copipe_data', [])
        parse_share.register(realid, data)
        twitter_api.sends(user_id, [f'{len(data)}件の講義データを登録しました'])
        copipe_procedure.set_progress(user_id, 2)
    else:
        twitter_api.sends(user_id, ['もう一度コピペしてください'])
        copipe_procedure.set_progress(user_id, 0)


ps = ProcedureSelectorDB(
    csv_procedure,
    time_procedure,
    status_procedure,
    delete_procedure,
    help_procedure,
    request_procedure,
    cources_procedure,
    copipe_procedure,
)
description = '電気通信大学・「個別配信型」休講情報ボット\n'\
    + f'{settings.url_prefix()}/#/\n\n'\
    + 'コマンドの一覧を表示します。以下のコマンドを送信することで対話的に設定できます。\n'\
    + ps.get_description()+'\n'\
    + '【end】 : 上記のすべてのコマンドを終了させます。'


def direct_message(user_id, msg_text, *args, **kwargs):
    msg = msg_text.strip().lower().translate(util.trans)
    if msg in ['end', 'quit', 'exit']:
        ps.end(user_id)
        return
    if ps.run(user_id, msg, raw=msg_text.strip()):
        return
    twitter_api.send(user_id, msg_text)


def follow(user_id):
    print(f'Followed by {user_id}')
    twitter_api.send(user_id, 'フォローありがとうございます！！！\n休講ボットにようこそ！')
    twitter_api.send(user_id, 'あなたに合わせた休講情報をお届けするには履修情報の登録が必要です')
    twitter_api.send(user_id, f'「csv」とメッセージを送信して、履修情報のアップロード用リンクを取得してください！ \n「copipe」で履修画面をコピペすることもできます\n参考：{settings.url_prefix()}/#/how-to-upload-csv')
