from urllib import parse
from io import BytesIO
import json
from http.cookies import SimpleCookie


def request(app, path, content_type, query={}, body='', method="GET",
            cookies={}, headers={}):
    ret = {}

    def start_response(status, headers):
        ret["status"] = status
        ret["headers"] = headers
        ret["cookies"] = {}
        cookies = SimpleCookie()
        for k, v in headers:
            if k == 'Set-Cookie':
                cookies.load(v)
        for key in cookies.keys():
            ret["cookies"][key] = cookies[key]
    env = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": parse.urlencode(query),
        'wsgi.input': BytesIO(bytearray(body, 'utf-8')),
        'CONTENT_LENGTH': len(body),
        'CONTENT_TYPE': content_type,
    }

    if headers:
        env.update({("HTTP_%s" % k).replace('-', '_').upper(): v
                    for k, v in headers.items()})

    if cookies:
        env['HTTP_COOKIE'] = ';'.join([k + '=' + v
                                       for k, v in cookies.items()])

    body = app(env, start_response)
    ret['body'] = ''.join(map(lambda x: x.decode(), body))
    return ret

def json_request(**kwargs):
    defaults = {
        "method": "POST",
        "content_type": "application/json"
    }
    defaults.update(kwargs)
    defaults['body'] = json.dumps(defaults['body'])
    return request(**defaults)

def form_request(app, path, body={}, **kwargs):
    kwargs.update({"app": app, "path": path, "body": body})
    defaults = {
        "content_type": "application/x-www-form-urlencoded"
    }
    defaults.update(kwargs)
    defaults['body'] = parse.urlencode(defaults['body'])
    return request(**defaults)

def get(app, path, query={}, **kwargs):
    kwargs.update({"app": app, "path": path, "query": query})
    defaults = {
        "method": "GET",
        "content_type": ""
    }
    defaults.update(kwargs)
    return request(**defaults)

def post(app, path, body={}, **kwargs):
    return form_request(app, path, body, method='POST', **kwargs)

def patch(app, path, body={}, **kwargs):
    return form_request(app, path, body, method='PATCH', **kwargs)
