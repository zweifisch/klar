from urllib import parse
from io import BytesIO
import json

def request(app, path, content_type, query={}, body='', method="GET"):
    ret = {}

    def start_response(status, headers):
        ret["status"] = status
        ret["headers"] = headers

    body = app({
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": parse.urlencode(query),
        'wsgi.input': BytesIO(bytearray(body, 'utf-8')),
        'CONTENT_LENGTH': len(body),
        'CONTENT_TYPE': content_type,
    }, start_response)
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

def post(**kwargs):
    defaults = {
        "method": "POST",
        "content_type": "application/x-www-form-urlencoded"
    }
    defaults.update(kwargs)
    defaults['body'] = parse.urlencode(defaults['body'])
    return request(**defaults)

def get(**kwargs):
    defaults = {
        "method": "GET",
        "content_type": ""
    }
    defaults.update(kwargs)
    return request(**defaults)
