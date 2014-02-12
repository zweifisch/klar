import types
import inspect
import re
import os
import json
from functools import partial
from urllib import parse

from jsonschema import validate


class App:

    def __init__(self):
        self.provider = Provider(
            router=Router,
            request=Request,
            response=Response,
        )

    def __getattr__(self, name):
        if name in ['get', 'post', 'delete', 'put', 'patch']:
            return partial(self.router.add_rule, name)
        elif self.provider.registered(name):
            component = getattr(self.provider, name)
            if not component:
                raise "failed to provide %s" % name
            return component

    def __call__(self, environ, start_response):
        self.provider.environ = environ
        status, headers, body = self.process_request()
        start_response(status, headers)
        return [body.encode('utf-8')]

    def process_request(self):
        handler, params = self.router.dispatch(self.environ['REQUEST_METHOD'],
                                               self.environ['PATH_INFO'])
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        status = 404
        body = ''
        if handler:
            status = 200
            params = dict(self.request.query, **params)
            response = handler(**self.prepare_params(handler, params))
            if tuple == type(response):
                for item in response:
                    if tuple is type(item):
                        key, value = item
                        headers[key] = value
                    elif int is type(item):
                        status = item
                    else:
                        body = item
            else:
                body = response
            if str is not type(body):
                body = json.dumps(body)
                headers = {'Content-Type': 'application/json; charset=utf-8'}
        return self.response.status(status), list(headers.items()), body

    def prepare_params(self, handler, params):
        ret = {}
        args = get_args(handler)
        for (name, default, default_available) in args:
            if self.provider.registered(name):
                params[name] = getattr(self.provider, name)
            elif default_available:
                params[name] = default
            else:
                if name not in params:
                    raise Exception("can't provide %s" % name)
        for name, anno in handler.__annotations__.items():
            if type(anno) is dict:
                validate(params[name], anno)
            elif isinstance(anno, type):
                params[name] = anno(params[name])
            elif hasattr(anno, '__tranform__'):
                params[name] = anno(params[name])
            elif hasattr(anno, '__validator__'):
                anno(params[name])
        return {name: params[name] for (name, *_) in args}

    def provide(self, name, component=None):
        if None is component:
            def decorate(fn):
                self.provider.register(name, fn)
                return fn
            return decorate
        else:
            self.provider.register(name, component)

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
        elif tuple is type(self.protos[name]):
            cls, params = self.protos[name]
            self.__dict__[name] = instance(cls, params, self)
        elif isinstance(self.protos[name], type):
            self.__dict__[name] = instance(self.protos[name], self)
        else:
            self.__dict__[name] = invoke(self.protos[name], self)
        return self.__dict__[name]

    def register(self, name, value):
        self.protos[name] = value

    def registered(self, name):
        return name in self.protos or name in self.__dict__


class Router:

    def __init__(self):
        self.rules = []

    def add_rule(self, method, pattern, handler=None):
        method = method.upper()
        if None is handler:
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
        return parse.parse_qs(self.environ['QUERY_STRING'])

    @property
    def body(self):
        body = self.environ['wsgi.input'].read()
        if self.content_type.start_with('application/json'):
            body = json.loads(body)
        elif self.content_type.start_with('application/x-www-form-urlencoded'):
            body = parse.parse_qs(body)
        return body

    @property
    def path(self):
        return self.environ['PATH_INFO']

    @property
    def method(self):
        return self.environ['REQUEST_METHOD']


class Response:

    @staticmethod
    def status(code):
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


class View:

    def __init__(self, root, ext='.html'):
        self.cached = {}
        self.root = root
        self.ext = ext

    def render(self, name, kvs):
        template = self.get_template(name)
        return template % {k: escape(v) for k, v in kvs.items()}

    def get_template(self, name):
        if name not in self.cached:
            with open(os.path.join(self.root, name) + self.ext) as f:
                html = f.read()
                self.cached[name] = re.sub(r'<%\s*(\w+)\s*%>', '%(\\1)s', html)
        return self.cached[name]


class Schema(type):
    pass


def escape(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def invoke(fn, *param_dicts):
    prepared_params = {}
    args = get_args(fn)
    for (name, value, default_available) in args:
        initial_value = value
        for params in param_dicts:
            if dict is type(params) and name in params:
                value = params[name]
                break
            elif hasattr(params, name):
                value = getattr(params, name)
                break
        if not default_available and value is initial_value:
            raise Exception("%s is required" % name)
        prepared_params[name] = value
    return fn(**prepared_params)


def instance(cls, *param_dicts):
    if isinstance(cls.__init__, types.FunctionType):
        return invoke(cls, *param_dicts)
    else:
        return cls()


def get_args(fn):
    sig = inspect.signature(fn)
    return [(p.name, p.default, p.default is not p.empty)
            for p in sig.parameters.values()
            if p.kind is p.POSITIONAL_OR_KEYWORD]
