import asyncio
from socketserver import ThreadingMixIn
from wsgiref.util import setup_testing_defaults
from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler

import json
from .route import Router

import sys
from .log import log
from .util import ignore_error
from .settings import settings
from concurrent.futures import ThreadPoolExecutor
import subprocess

import json
import time


def execute(environ, start_response):
    try:
        status, headers, ret = Router.do(environ)
        ip = environ["HTTP_X_REAL_IP"] if ("HTTP_X_REAL_IP" in environ) else environ["REMOTE_ADDR"]
        req_id = environ["HTTP_X_REQUEST_ID"] if "HTTP_X_REQUEST_ID" in environ else ""
        log(__name__, f'{ip.ljust(15)}  |  {status.ljust(15)}  [{environ["REQUEST_METHOD"].ljust(5)}] {environ["PATH_INFO"]}  ({environ["SERVER_PROTOCOL"]}) {req_id}')
        start_response(status, headers)
        return ret
    except Exception as e:
        print(e.with_traceback())
        start_response("500 ", [])
        return []


pool = ThreadPoolExecutor(1000)


def app(environ, start_response):
    return pool.submit(execute, environ, start_response).result()


class NoLoggingWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


class ThreadingWsgiServer(ThreadingMixIn, WSGIServer):
    pass


def run_server():
    port = settings["port"]
    try:
        pass
        # subprocess.check_call(['bash', '-c', f'kill -9 `lsof -t -i:{port}`'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass
    finally:
        time.sleep(1)
    with make_server('0.0.0.0', port, app, WSGIServer, handler_class=NoLoggingWSGIRequestHandler) as httpd:
        log(__name__, f'Listen on port: {port}')
        httpd.serve_forever()
