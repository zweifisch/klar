import types
import inspect
import re
import os
import json
import time
from functools import partial
from urllib import parse
from http.cookies import SimpleCookie

from jsonschema import validate
from jsonschema.exceptions import ValidationError, SchemaError

class App:

    def __init__(self):
        self.provider = Provider(
            router=Router,
            request=Request,
            cookies=Cookies
        )

        @self.provide('body')
        def body(request):
            return request.body

    def __getattr__(self, name):
        if name in ['get', 'post', 'delete', 'put', 'patch']:
            return partial(self.provider.router.add_rule, name)
        else:
            raise HttpError(500, "method %s not exists" % name)

    def __call__(self, environ, start_response):
        self.provider.environ = environ
        try:
            status, headers, body = self.process_request()
        except HttpError as e:
            status, body = e.args
            headers = []
        processed = self.process_hooks()
        if processed:
            status, headers, body = processed
        status, headers, body = self.format_response(status, headers, body)

        cookies = self.provider.cookies.output()
        if cookies:
            headers.extend(cookies)

        del self.provider.request
        del self.provider.body
        del self.provider.cookies
        start_response(status, headers)
        return [body.encode('utf-8')]

    def process_hooks(self):
        pass

    def format_response(self, status, headers, body):
        default_headers = {'Content-Type': 'text/html; charset=utf-8'}
        if type(body) is not str:
            body = json.dumps(body)
            headers = {'Content-Type': 'application/json; charset=utf-8'}
        default_headers.update(headers)
        return get_status(status), list(default_headers.items()), body

    def process_request(self):
        handler, params = self.provider.router.dispatch(
            self.provider.request.method, self.provider.request.path)
        headers = {}
        status = 404
        body = ''
        if handler:
            status = 200
            params = dict(self.provider.request.query, **params)
            try:
                prepared_params = self.prepare_params(handler, params)
            except ValidationError as e:
                return 400, [], e.message
            except SchemaError as e:
                return 500, [], e.message
            try:
                response = handler(**prepared_params)
            except Exception as e:
                return 500, [], str(e)
            return_anno = handler.__annotations__.get('return')
            if callable(return_anno):
                response = return_anno(response)
            elif type(return_anno) is tuple:
                for post_processer in return_anno:
                    response = post_processer(*response)
            if tuple == type(response):
                for item in response:
                    if type(item) is tuple:
                        key, value = item
                        headers[key] = value
                    elif type(item) is int:
                        status = item
                    else:
                        body = item
            else:
                body = response
        return status, headers, body

    def prepare_params(self, handler, params):
        ret = {}
        args, *_ = inspect.getargs(handler.__code__)
        params = dict(get_arg_defaults(handler), **params)
        for name in args:
            if self.provider.registered(name):
                params[name] = getattr(self.provider, name)

            if name not in params:
                if name in handler.__annotations__:
                    raise HttpError(400, "%s is required" % name)
                else:
                    raise HttpError(500, "can't provide %s" % name)

            if name in handler.__annotations__:
                anno = handler.__annotations__[name]
                if type(anno) is dict:
                    validate(params[name], anno)
                elif callable(anno):
                    params[name] = anno(params[name])
                else:
                    raise HttpError(500, "unrecognized annotation type for %s" % name)

        return {name: params[name] for name in args}

    def provide(self, name, component=None):
        if component is None:
            def decorate(fn):
                self.provider.register(name, fn)
                return fn
            return decorate
        else:
            self.provider.register(name, component)

    def on(self, event):
        pass

    def run(self, port=3000):
        from wsgiref.simple_server import make_server
        print('listen on %s' % port)
        make_server('', port, self).serve_forever()


class Provider:

    def __init__(self, protos=None, **kwargs):
        self.protos = protos or kwargs

    def __getattr__(self, name):
        if name not in self.protos:
            raise Exception("%s not registered" % name)
        elif type(self.protos[name]) is tuple:
            cls, params = self.protos[name]
            self.__dict__[name] = instance(cls, params, self)
        elif isinstance(self.protos[name], type):
            self.__dict__[name] = instance(self.protos[name], self)
        else:
            self.__dict__[name] = invoke(self.protos[name], self)
        return self.__dict__[name]

    def __delattr__(self, name):
        if name in self.__dict__:
            del self.__dict__[name]

    def register(self, name, value):
        self.protos[name] = value

    def registered(self, name):
        return name in self.protos or name in self.__dict__


class Router:

    def __init__(self):
        self.rules = []

    def add_rule(self, method, pattern, handler=None):
        method = method.upper()
        if handler is None:
            def decorate(handler):
                self.rules.append((method, self.parse_url(pattern), handler))
                return handler
            return decorate
        self.rules.append((method, self.parse_url(pattern), handler))

    def parse_url(self, pattern):
        keys = re.findall(r'<([^>]+)>', pattern)
        pattern = re.compile('^%s$' % re.sub(r'<[^>]+>', '([^/]+)', pattern))
        return keys, pattern

    def dispatch(self, method, path):
        for _method, (keys, pattern), handler in self.rules:
            if _method != method:
                continue
            result = pattern.match(path)
            if result:
                return handler, dict(zip(keys, result.groups()))
        return None, None

    def __repr__(self):
        return "\n".join(["%s %s -> %s" % (method, r.pattern, handler.__qualname__)
                          for (method, (keys, r), handler) in self.rules])


class Request:

    def __init__(self, environ):
        self.environ = environ

    def env(self, key, default=None):
        return self.environ.get(key) or default

    @property
    def content_type(self):
        return self.environ['CONTENT_TYPE']

    @property
    def query(self):
        return dict(parse.parse_qsl(self.environ['QUERY_STRING']))

    @property
    def body(self):
        content_length = int(self.environ.get('CONTENT_LENGTH', 0))
        if content_length == 0:
            return {}
        body = self.environ['wsgi.input'].read(content_length).decode()
        if self.content_type.startswith('application/json'):
            body = json.loads(body)
        elif self.content_type.startswith('application/x-www-form-urlencoded'):
            body = dict(parse.parse_qsl(body))
        return body

    @property
    def path(self):
        return self.environ['PATH_INFO']

    @property
    def method(self):
        return self.environ['REQUEST_METHOD'].upper()


class Cookies:

    units = {
        "day": 86400,
        "days": 86400,
        "hour": 3600,
        "hours": 3600,
        "minute": 60,
        "minutes": 60,
    }

    def __init__(self, environ):
        self.cookies = SimpleCookie()
        if 'HTTP_COOKIE' in environ:
            self.cookies.load(environ['HTTP_COOKIE'])
        self.changed_keys = []

    def get(self, key):
        return self.cookies[key].value if key in self.cookies else None

    def set(self, key, value, **kwargs):
        self.cookies[key] = value
        if 'expires' in kwargs:
            kwargs['expires'] = time.strftime("%a, %d-%b-%Y %T GMT",
                                              kwargs['expires'])
        for k, v in kwargs.items():
            self.cookies[key][k] = v
        self.changed_keys.append(key)

    def __getattr__(self, key):
        if key.startswith('set_for_'):
            tokens = iter(key[8:].split('_'))
            total = 0
            for quantity, unit in zip(tokens, tokens):
                total += int(quantity) * self.units[unit]
            expires = time.time() + total
            return partial(self.set, expires=time.gmtime(expires))
        else:
            raise HttpError(500, '%s not exists' % key)

    def delete(self, key):
        if key in self.cookies:
            self.set(key, '', expires=time.gmtime(0))

    def output(self):
        return [('Set-Cookie', self.cookies[key].OutputString())
                for key in self.cookies if key in self.changed_keys]


class EventEmitter:

    def trigger(self, event, **kargs):
        pass


class HttpError(Exception):
    pass


def invoke(fn, *param_dicts):
    prepared_params = {}
    args = get_args(fn)
    defaults = get_arg_defaults(fn)
    for name in args:
        for params in param_dicts:
            if type(params) is dict and name in params:
                prepared_params[name] = params[name]
                break
            elif hasattr(params, name):
                prepared_params[name] = getattr(params, name)
                break
        if name not in prepared_params:
            if name in defaults:
                prepared_params[name] = defaults[name]
            else:
                raise Exception("%s is required" % name)
    return fn(**prepared_params)

def instance(cls, *param_dicts):
    if isinstance(cls.__init__, types.FunctionType):
        return invoke(cls, *param_dicts)
    else:
        return cls()

def get_arg_defaults(fn):
    sig = inspect.signature(fn)
    return {p.name: p.default for p in sig.parameters.values()
            if p.kind is p.POSITIONAL_OR_KEYWORD and p.default is not p.empty}

def get_args(fn):
    sig = inspect.signature(fn)
    return [p.name for p in sig.parameters.values()
            if p.kind is p.POSITIONAL_OR_KEYWORD]

def get_status(code):
    return {
        200: '200 OK',
        201: '201 Created',
        202: '202 Accepted',
        203: '203 Non-Authoritative Information',
        204: '204 No Content',
        205: '205 Reset Content',
        206: '206 Partial Content',
        300: '300 Multiple Choices',
        301: '301 Moved Permanently',
        302: '302 Found',
        304: '304 Not Modified',
        305: '305 Use Proxy',
        307: '307 Temporary Redirect',
        400: '400 Bad Request',
        401: '401 Unauthorized',
        403: '403 Forbidden',
        404: '404 Not Found',
        405: '405 Method Not Allowed',
        406: '406 Not Acceptable',
        407: '407 Proxy Authentication Required',
        408: '408 Request Timeout',
        409: '409 Conflict',
        410: '410 Gone',
        411: '411 Length Required',
        412: '412 Precondition Failed',
        413: '413 Request Entity Too Large',
        414: '414 Request-URI Too Long',
        415: '415 Unsupported Media Type',
        416: '416 Requested Range Not Satisfiable',
        417: '417 Expectation Failed',
        500: '500 Internal Server Error',
        501: '501 Not Implemented',
        502: '502 Bad Gateway',
        503: '503 Service Unavailable',
        504: '504 Gateway Timeout',
        505: '505 HTTP Version Not Supported'}.get(code)
