import sys
from datetime import datetime
import os
from threading import Lock
import requests
isinpackage = not __name__ in ['log', '__main__']
if isinpackage:
    from .settings import settings
    from . import scheduler
else:
    from settings import settings

log_lock = Lock()
log_file = None


def log(__name__, message, log_level=2):
    '''
    ## log level
    6 = REQUEST
    5 = FATAL
    4 = ERROR
    3 = WARN
    2 = INFO (default)
    1 = DEBUG
    0 = TRACE
    '''
    global log_file
    now = datetime.now()
    log_file = log_file or os.path.join(os.path.dirname(__file__), settings.logfile())
    msg = f'{now}  |  [{__name__.ljust(20)}]  {message}'
    with log_lock:
        if log_level >= settings.log_level(0):
            sys.stdout.write(msg)
            sys.stdout.write('\n')
            sys.stdout.flush()
        if settings.log.slack() and log_level >= settings.log.slack.log_level_gt():
            scheduler.pool.submit(log_with_slack, now, __name__, message, log_level)
        with open(log_file, 'at', encoding='utf-8') as f:
            f.write(msg+'\n')


LOG_LEVEL = [
    {'text': 'TRACE', 'color': '#607D8B'},
    {'text': 'DEBUG', 'color': '#3F51B5'},
    {'text': 'INFO', 'color': '#03A9F4'},
    {'text': 'WARN', 'color': '#FFC107'},
    {'text': 'ERROR', 'color': '#F44336'},
    {'text': 'FATAL', 'color': '#E91E63'},
    {'text': 'REQUEST', 'color': '#03A9F4'}
]


def log_with_slack(time, module_name, message, log_level):
    res = requests.post(settings.log.slack.slack_webhook(), json={
        "attachments": [
            {
                "fallback": f"Log: {LOG_LEVEL[log_level]['text']}",
                "color": LOG_LEVEL[log_level]['color'],
                "title": LOG_LEVEL[log_level]['text'],
                "footer": "ご注文は休講情報ですか？",
                "text": module_name,
                "footer_icon": "https://kyukou.monoid.app/_media/logo-250.png",
            }
        ],
        "text": f"```{message}```",
        "mrkdwn": True
    })
    print(res.text)
    return res.status_code == 200
