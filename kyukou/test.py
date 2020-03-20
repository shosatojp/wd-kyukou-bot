from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler



def run_server():
    with make_server('localhost', 5426, app) as httpd:
        httpd.serve_forever()


def app(environ, start_response):
    start_response("200 OK", [])
    return []

run_server()