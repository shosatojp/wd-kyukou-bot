import os
import yaml
import json
from threading import Lock
settings = {}
env_mark = '__ENV__'

isinpackage = not __name__ in ['settings', '__main__']
if isinpackage:
    from .util import Just
    from .config import config
else:
    from util import Just
    from config import config


def load_settings(relative_path):
    path = os.path.join(os.path.dirname(__file__), relative_path)
    with open(path, 'rt', encoding='utf-8') as f:
        global settings
        settings = config
        resolve_env(settings)
        settings = Just(settings)


def get_settings():
    return settings


def resolve_env(d):
    tmp = {}
    for key in d.keys():
        value = d[key]
        if isinstance(value, dict):
            resolve_env(value)
        else:
            if key.startswith(env_mark):
                name = key[len(env_mark):]
                tmp[name] = os.environ.get(value)
    d.update(**tmp)


STORE_FILE = os.path.join(os.path.dirname(__file__), 'storage')
store_lock = Lock()


def load_basic(file):
    if os.path.exists(file):
        with store_lock:
            with open(file, 'rt', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except:
                    return {}
    else:
        return {}


def store_basic(file, obj):
    with store_lock:
        with open(file, 'wt', encoding='utf-8') as f:
            json.dump(obj, f)


def load(key, default):
    return load_basic(STORE_FILE).get(key) or default


def store(key, value):
    obj = load_basic(STORE_FILE)
    obj[key] = value
    store_basic(STORE_FILE, obj)


if not isinpackage:
    load_settings('config.yml')
