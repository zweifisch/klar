import os
import re
import json
import types
import random
import inspect
import traceback
import mimetypes
from functools import partial
from urllib import parse
from http.cookies import SimpleCookie
import http.client
from cgi import FieldStorage, parse_header

from jsonschema import validate
from jsonschema.exceptions import ValidationError, SchemaError


class App:

    rules = [
        ('GET',    '%(path)s',               'query'),
        ('POST',   '%(path)s',               'create'),
        ('GET',    '%(path)s/<%(id)s>',      'show'),
        ('PUT',    '%(path)s/<%(id)s>',      'replace'),
        ('PATCH',  '%(path)s/<%(id)s>',      'modify'),
        ('DELETE', '%(path)s/<%(id)s>',      'destroy'),
        ('GET',    '%(path)s/new',           'new'),
        ('GET',    '%(path)s/<%(id)s>/edit', 'edit'),
    ]

    methods = [method for _, _, method in rules]

    def __init__(self):
        self.provider = Provider(
            router=Router,
            request=Request,
            cookies=Cookies,
            cache=Cache,
            session=Session,
            response=Response,
            emitter=EventEmitter,
        )

        @self.provide('provider')
        def provider():
            return self.provider

        @self.provide('body')
        def body(request):
            return request.body

        @self.provide('uploads')
        def uploads(request):
            return request.uploads

    def __getattr__(self, name):
        if name in ['get', 'post', 'delete', 'put', 'patch', 'head']:
            return partial(self.provider.router.add_rule, name)
        else:
            raise HttpError(500, "method %s not exists" % name)

    def __call__(self, environ, start_response):
        self.provider.environ = environ
        try:
            code, headers, body = self.process_request()
        except HttpError as e:
            code, body = e.args
            headers = []
        except Exception as e:
            return 500, [], traceback.format_exc().replace("\n", "\n<br>")
        processed = self.process_hooks()
        if processed:
            code, headers, body = processed
        self.provider.emitter.emit(code)
        status, headers, body = self.format_response(code, headers, body)

        if code != 500:
            self.provider.session.flush()
            cookies = self.provider.cookies.output()
            if cookies:
                headers.extend(cookies)

        del self.provider.request
        del self.provider.body
        del self.provider.uploads
        del self.provider.cookies
        del self.provider.session
        start_response(status, headers)
        if type(body) is str:
            body = body.encode('utf-8')
        return [body]

    def process_hooks(self):
        pass

    def format_response(self, status, headers, body):
        default_headers = {'Content-Type': 'text/html; charset=utf-8'}
        if body is None:
            body = ''
        if type(body) not in [str, bytes]:
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
                print(traceback.format_exc())
                return 500, [], "Error in schema: " + e.message
            response = handler(**prepared_params)
            return_anno = handler.__annotations__.get('return')
            if callable(return_anno):
                response = return_anno(response)
            elif type(return_anno) is tuple:
                for post_processer in return_anno:
                    response = post_processer(*response)
            if type(response) == tuple:
                for item in response:
                    if type(item) is tuple:
                        key, value = item
                        headers[key] = value
                    elif type(item) is int:
                        status = item
                    else:
                        body = item
            elif type(response) == int:
                status = response
            else:
                body = response
        return status, headers, body

    def prepare_params(self, handler, params):
        args = inspect.getargs(handler.__code__)[0]
        params = dict(get_arg_defaults(handler), **params)
        for name in args:
            if hasattr(self.provider, name):
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
                    raise HttpError(500, "unrecognized annotation type for %s"
                                    % name)
        return {name: params[name] for name in args}

    def provide(self, name, component=None):
        if component is None:
            def decorate(fn):
                self.provider.register(name, fn)
                return fn
            return decorate
        else:
            self.provider.register(name, component)

    def on(self, event, handler=None):
        if handler:
            return self.provider.emitter.register(event, handler)
        else:
            return partial(self.provider.emitter.register, event)

    def run(self, port=3000):
        from wsgiref.simple_server import make_server
        print('listen on %s' % port)
        make_server('', port, self).serve_forever()

    def resource(self, url_path=None, module=None):
        if url_path is None:
            url_path = '/' + module.__name__.replace('.', '/')
        if module is None:
            return partial(self.register_resource, url_path)
        else:
            self.register_resource(url_path, module)

    def register_resource(self, url_path, module):
        url_id = '%s_id' % url_path.split('/').pop()
        vals = {'path': url_path, 'id': url_id}
        rules = [(method, pattern % vals, getattr(module, handler))
                 for method, pattern, handler in self.rules
                 if hasattr(module, handler)]

        if isinstance(type(module), types.ModuleType):
            fns = get_module_fns(module)
        else:
            fns = get_methods(module)

        custom_rules = [(getattr(fn, '__httpmethod__', 'GET'),
                        '%s/<%s>/%s' % (url_path, url_id, fn.__name__),
                        fn) for fn in fns if fn.__name__ not in self.methods]
        self.provider.router.add_rules(rules)
        self.provider.router.add_rules(custom_rules)

    def resources(self, *resources, prefix=''):
        for resource in resources:
            url_path = prefix + '/' + resource.__name__.split('.').pop()
            self.register_resource(url_path, resource)

    def static(self, url_root, fs_root=None):
        if fs_root is None:
            fs_root = url_root[1:]
        self.provider.router.add_rule('GET', re.compile(
            "^" + url_root + "(?P<url>.+)$"), static_handler(fs_root))


class Provider:

    def __init__(self, protos=None, **kwargs):
        self.protos = protos or kwargs

    def __getattr__(self, name):
        if name not in self.protos:
            raise AttributeError("%s not registered" % name)
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


class Router:

    def __init__(self):
        self.rules = []

    def add_rule(self, method, pattern, handler=None):
        method = method.upper()
        if type(pattern) is str:
            pattern = self.parse_pattern(pattern)
        if handler is None:
            def decorate(handler):
                self.rules.append((method, pattern, handler))
                return handler
            return decorate
        self.rules.append((method, pattern, handler))

    def add_rules(self, rules):
        for rule in rules:
            self.add_rule(*rule)

    def parse_pattern(self, pattern):
        pattern = re.compile('^%s$' %
                             re.sub(r'<([^>]+)>', r'(?P<\1>[^/]+)', pattern))
        return pattern

    def dispatch(self, method, path):
        for _method, pattern, handler in self.rules:
            if _method != method:
                continue
            result = pattern.match(path)
            if result:
                return handler, result.groupdict()
        return None, None

    def __repr__(self):
        return "\n".join(["%s %s -> %s" %
                          (method, pattern.pattern, handler.__qualname__)
                          for (method, pattern, handler) in self.rules])


class Request:

    def __init__(self, environ):
        self.environ = environ

    def env(self, key, default=None):
        return self.environ.get(key, default)

    @property
    def content_type(self):
        return parse_header(self.environ['CONTENT_TYPE'])

    @property
    def query(self):
        return dict(parse.parse_qsl(self.environ['QUERY_STRING']))

    @property
    def body(self):
        if not hasattr(self, '_body'):
            self.parse_body()
        return self._body

    def parse_body(self):
        content_type, _ = self.content_type
        if content_type == 'application/json':
            self._body = json.loads(self.get_raw_body())
        elif content_type == 'application/x-www-form-urlencoded':
            self._body = dict(parse.parse_qsl(self.get_raw_body()))
        elif content_type == 'multipart/form-data':
            fs = FieldStorage(self.environ['wsgi.input'], environ=self.environ)
            self._body, self._uploads = {}, {}
            for name in fs.keys():
                if fs[name].filename is None:
                    self._body[name] = fs[name].value
                else:
                    self._uploads[name] = fs[name]

    def get_raw_body(self):
        content_length = int(self.environ.get('CONTENT_LENGTH', 0))
        if content_length == 0:
            return ''
        return self.environ['wsgi.input'].read(content_length).decode()

    @property
    def uploads(self):
        if not hasattr(self, '_uploads'):
            self.parse_body()
        return self._uploads

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

    def get(self, key, default=None):
        return self.cookies[key].value if key in self.cookies else default

    def set(self, key, value, **kwargs):
        self.cookies[key] = value
        for k, v in kwargs.items():
            self.cookies[key][k] = v
        self.changed_keys.append(key)

    def __getattr__(self, key):
        if key.startswith('set_for_'):
            tokens = iter(key[8:].split('_'))
            total = 0
            for quantity, unit in zip(tokens, tokens):
                total += int(quantity) * self.units[unit]
            return partial(self.set, expires=int(total))
        else:
            raise HttpError(500, '%s not exists' % key)

    def delete(self, key):
        if key in self.cookies:
            self.set(key, '', expires='Thu, 01 Jan 1970 00:00:00 GMT')

    def output(self):
        return [('Set-Cookie', self.cookies[key].OutputString())
                for key in self.cookies if key in self.changed_keys]


class Session:

    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'

    def __init__(self, cookies, cache, sid_key='ksid', key_len=16,
                 key_prefix='sid:'):
        self.cache = cache
        self.cookies = cookies
        self.sid_key = sid_key
        self.key_len = key_len
        self.key_prefix = key_prefix

        sid = self.cookies.get(sid_key)
        self.data = {}
        if sid and self.load(sid):
            self._sid = sid
        self.is_dirty = False

    @property
    def sid(self):
        if not hasattr(self, '_sid'):
            self._sid = ''.join(random.choice(self.chars)
                                for i in range(self.key_len))
            self.cookies.set(self.sid_key, self._sid, httponly=True)
        return self._sid

    def load(self, sid):
        data = self.cache.get(self.key_prefix + sid)
        self.data = data or {}
        return data

    def get(self, key, default=None):
        return self.data[key] if key in self.data else default

    def set(self, key, value):
        self.is_dirty = True
        self.data[key] = value

    def delete(self, key):
        if key in self.data:
            self.is_dirty = True
            del self.data[key]

    def destroy(self):
        self.data = {}
        self.cache.delete(self.key_prefix + self.sid)
        self.cookies.delete(self.sid_key)
        self.is_dirty = False

    def flush(self):
        if self.is_dirty:
            self.cache.set(self.key_prefix + self.sid, self.data)
            self.is_dirty = False


class Cache:
    "should not be use in production"

    def get(self, key):
        return self.__dict__.get(key)

    def set(self, key, value):
        self.__dict__[key] = value

    def delete(self, key):
        del self.__dict__[key]


class EventEmitter:

    def __init__(self, provider):
        self.listeners = {}
        self.provider = provider

    def emit(self, event, **kargs):
        if event in self.listeners:
            for listener in self.listeners[event]:
                invoke(listener, kargs, self.provider)

    def register(self, event, handler):
        if event in self.listeners:
            self.listeners[event].append(handler)
        else:
            self.listeners[event] = [handler]


class Config:
    pass


class Response:
    pass


class HttpError(Exception):
    pass


def invoke(fn, *param_dicts):
    "call a function with a list of dicts providing params"
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
    "get instance of a given class"
    if isinstance(cls.__init__, types.FunctionType):
        return invoke(cls, *param_dicts)
    else:
        return cls()


def get_arg_defaults(fn):
    "get arguments with default values as a dict"
    sig = inspect.signature(fn)
    return {p.name: p.default for p in sig.parameters.values()
            if p.kind is p.POSITIONAL_OR_KEYWORD and p.default is not p.empty}


def get_args(fn):
    "get argument names of a function as a list of strings"
    sig = inspect.signature(fn)
    return [p.name for p in sig.parameters.values()
            if p.kind is p.POSITIONAL_OR_KEYWORD]


def get_status(code):
    "get status using http code"
    if code not in http.client.responses:
        raise HttpError(500, '%s is not a valide status code' % code)
    return "%s %s" % (code, http.client.responses[code])


def redirect(url, permanent=False):
    code = 301 if permanent else 302
    return code, ('Location', url)


def static_handler(fs_root):
    if not os.path.isdir(fs_root):
        raise HttpError(500, "static root %s should be a dir" % fs_root)

    def handler(url):
        fs_path = os.path.join(fs_root, url)
        if not os.path.isfile(fs_path):
            return 404, "%s not exists" % fs_path
        mimetype, _ = mimetypes.guess_type(fs_path)
        fp = open(fs_path)
        return fp.read(), ('Content-Type',
                           mimetype or 'application/octet-stream')
    return handler


def get_module_fns(module):
    "get defined functions of module"
    attrs = [getattr(module, a) for a in dir(module) if not a.startswith('_')]
    return [attr for attr in attrs if isinstance(attr, types.FunctionType)
            and attr.__module__ == module.__name__]


def get_methods(cls):
    "get public methods of a class"
    attrs = [getattr(cls, a) for a in dir(cls) if not a.startswith('_')]
    return [attr for attr in attrs if isinstance(attr, types.FunctionType)]


def method(httpmethod):
    "decorator to overwrite default method(GET) for custom actions"
    def add_method(fn):
        fn.__httpmethod__ = httpmethod
        return fn
    return add_method
