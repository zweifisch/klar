from klar import App, method, etag
from request import get, json_request, post, patch
import json
import datetime


class TestApp:

    def test_hello(self):
        app = App()

        @app.get('/hello/<name>')
        def hello(name: str, times: int=1):
            return "hello " * times + name

        response = get(app, '/hello/klar', {"times": 2})
        assert response['body'] == "hello hello klar"

    def test_routing(self):
        app = App()

        @app.get('/')
        def index():
            return 'index'

        @app.get('/foo')
        def foo():
            return 'foo'

        @app.route('/bar', methods=['get', 'post', 'put'])
        def bar(request):
            return '%s: %s' % (request.method, request.path)

        assert get(app, '/')['body'] == 'index'
        assert get(app, '/foo')['body'] == 'foo'
        assert get(app, '/baz')['status'].startswith('404')
        assert get(app, '/bar')['body'] == 'GET: /bar'
        assert post(app, '/bar')['body'] == 'POST: /bar'

    def test_params(self):
        app = App()

        @app.get('/')
        def index(q: str):
            return q

        assert get(app=app, path='/', query={"q": "str"})['body'] == 'str'

    def test_json(self):
        app = App()

        @app.post('/create')
        def create(body):
            return body

        body = {"key": "value"}
        assert json_request(app=app, path='/create',
                            body=body)['body'] == json.dumps(body)

    def test_schema(self):
        app = App()

        @app.post('/create')
        def create(body: {"type": "array"}):
            return body

        body = ["key", "value"]
        assert json_request(app=app, path='/create',
                            body=body)['body'] == json.dumps(body)

        body = {"key": "value"}
        assert json_request(app=app, path='/create',
                            body=body)['status'].startswith('400')

    def test_type(self):
        app = App()

        @app.get('/test/<bar>')
        def index(bar: int, foo: int=0):
            return str(bar + foo)

        assert get(app=app, path='/test/200')['body'] == '200'

        response = get(app=app, path='/test/200', query={"foo": 1})
        assert response['body'] == '201'

    def test_template_rendering(self):
        app = App()

        import templates.test

        @app.get('/test')
        def test(key) -> templates.test:
            return {"key": key}

        assert get(app, '/test', {"key": "foo"})['body'] == "key is foo\n"

    def test_cookie(self):

        app = App()

        @app.get('/test')
        def test(cookies):
            return cookies.get('id')

        @app.get('/test-set')
        def test2(cookies):
            cookies.set('foo', 'bar')
            return ''

        @app.get('/test-expires')
        def test3(cookies):
            cookies.set_for_30_days('foo', 'bar', httponly=True)
            return ''

        @app.get('/test-delete')
        def test4(cookies):
            cookies.delete('id')
            return ''

        assert get(app, '/test', cookies={"id": "foo"})['body'] == "foo"

        expected = [('Content-Type', 'text/html; charset=utf-8'),
                    ('Set-Cookie', 'foo=bar')]
        res = get(app, '/test-set', cookies={"id": "foo"})
        assert res["status"] == "200 OK"
        assert res["headers"] == expected

        fmt = "%a, %d %b %Y %H:%M:%S GMT"
        expires = (datetime.datetime.utcnow() +
                   datetime.timedelta(days=30)).strftime(fmt)
        expected = [('Content-Type', 'text/html; charset=utf-8'),
                    ('Set-Cookie', 'foo=bar; expires=%s; httponly' % expires)]
        response = get(app, '/test-expires', cookies={"id": "foo"})
        assert response['headers'] == expected

        expires = datetime.datetime.utcfromtimestamp(0).strftime(fmt)
        expected = [('Content-Type', 'text/html; charset=utf-8'),
                    ('Set-Cookie', 'id=''; expires=%s' % expires)]
        res = get(app, '/test-delete', cookies={"id": "foo"})
        assert res["status"] == "200 OK"
        assert res["headers"] == expected

    def test_session(self):

        app = App()

        @app.get('/test')
        def test(session):
            if session.get('userid'):
                return 'userid: %s' % session.get('userid')
            return 'not logged in'

        @app.post('/login')
        def login(body, session):
            if body['username'] == 'admin' and body['passwd'] == 'secret':
                session.set('userid', 123)
                return 'logged in'
            return 'failed'

        @app.post('/logout')
        def logout(session):
            if session.get('userid'):
                session.destroy()
                return 'logged out'

        res = post(app, '/login', {'username': 'admin', 'passwd': 'secret'})
        assert res['status'] == '200 OK'
        assert res['body'] == 'logged in'
        assert res['headers'][1][0] == 'Set-Cookie'
        assert res['headers'][1][1].startswith('ksid=')
        sid = res['headers'][1][1][5:]

        res = get(app, '/test')
        assert res['status'] == '200 OK'
        assert res['body'] == 'not logged in'

        res = get(app, '/test', cookies={"ksid": sid})
        assert res['status'] == '200 OK'
        assert res['body'] == 'userid: 123'

        res = post(app, '/logout', cookies={"ksid": sid})
        assert res['status'] == '200 OK'
        assert res['body'] == 'logged out'

        res = get(app, '/test', cookies={"ksid": sid})
        assert res['status'] == '200 OK'
        assert res['body'] == 'not logged in'

    def test_response(self):

        app = App()

        @app.get('/')
        def test():
            return 404

        res = get(app, '/')
        assert res['status'] == '404 Not Found'

    def test_resource_cls(self):

        app = App()

        @app.resource('/v1/post')
        class PostResource:
            def show(post_id):
                return 'post: %s' % post_id

            @method('patch')
            def like(post_id):
                return 'liked: %s' % post_id

        res = get(app, '/v1/post/31415')
        assert res['status'] == '200 OK'
        assert res['body'] == 'post: 31415'

        res = get(app, '/v1/post/3141/like')
        assert res['status'].startswith('404')

        res = patch(app, '/v1/post/3141/like')
        assert res['status'].startswith('200')

    def test_resource_module(self):

        app = App()

        from resources import post
        app.resource(module=post)

        res = get(app, '/resources/post/314')
        assert res['status'] == '200 OK'
        assert res['body'] == 'post: 314'

        app = App()

        from resources import post
        app.resource('/v1/post', post)

        res = get(app, '/v1/post/3141')
        assert res['status'] == '200 OK'
        assert res['body'] == 'post: 3141'

        res = get(app, '/v1/post/31415/downvote')
        assert res['status'].startswith('404')

        res = patch(app, '/v1/post/31415/upvote')
        assert res['status'].startswith('200')
        assert res['body'] == 'upvote: 31415'

    def test_resources(self):

        app = App()

        from resources import post
        app.resources(post, prefix='/v2')

        res = get(app, '/v2/post/31')
        assert res['status'] == '200 OK'
        assert res['body'] == 'post: 31'

    def test_event(self):
        app = App()

        @app.get('/')
        def home(emitter):
            emitter.emit('foo', bar='visited')

        @app.on('foo')
        def handle_foo(bar, cookies):
            cookies.set('event', bar)

        @app.on(200)
        def handle_200(cookies):
            cookies.set('code', 200)

        res = get(app, '/')
        assert res['cookies']['event'].value == 'visited'
        assert res['cookies']['code'].value == '200'

    def test_response_processing(self):
        app = App()

        def jsonp(body, request):
            callback = request.query.get('callback')
            if callback:
                body = "%s(%s)" % (callback, json.dumps(body))
                return body, ("Content-Type", "application/javascript")

        @app.get('/')
        def handler() -> jsonp:
            return {'key': 'value'}

        res = get(app, '/', dict(callback='cb'))
        assert res['body'] == 'cb({"key": "value"})'
        assert res['headers'] == [("Content-Type", "application/javascript")]

        res = get(app, '/')
        assert res['status'] == '200 OK'
        assert res['body'] == '{"key": "value"}'

    def test_ajax(self):
        app = App()

        @app.get('/api')
        def ajax(request):
            return "ajax" if request.is_ajax else "not ajax"
        res = get(app, '/api', headers={"X-Requested-With": "XMLHttpRequest"})
        assert res['body'] == 'ajax'

    def test_etag(self):
        app = App()

        @app.get('/etag')
        def handler(request) -> etag:
            return "content"

        res = get(app, '/etag')
        assert res['body'] == 'content'
        assert res['status'] == '200 OK'

        headers = dict(res['headers'])
        res = get(app, '/etag', headers={"If-None-Match": headers['Etag']})
        assert res['status'].startswith('304')
        assert res['body'] == ''

        headers = dict(res['headers'])
        res = get(app, '/etag', headers={"If-None-Match": 'etag'})
        assert res['status'].startswith('200')
        assert res['body'] == 'content'

    def test_last_modified(self):
        app = App()

        @app.get('/last-modified')
        def handler():
            now = datetime.datetime.utcnow().replace(microsecond=0)
            return "content", ("Last-Modified", now)

        res = get(app, '/last-modified')
        assert res['body'] == 'content'
        assert res['status'] == '200 OK'

        now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        res = get(app, '/last-modified', headers={"If-Modified-Since": now})
        assert res['body'] == 'content'
        assert res['status'].startswith('200')

        yesterday = datetime.datetime.utcnow() + datetime.timedelta(days=-1)
        yesterday = yesterday.strftime("%a, %d %b %Y %H:%M:%S GMT")
        res = get(app, '/last-modified', headers={"If-Modified-Since":
                                                  yesterday})
        assert res['body'] == ''
        assert res['status'].startswith('304')

        res = get(app, '/last-modified', headers={"If-Modified-Since": 'yesterday'})
        assert res['body'] == 'content'
        assert res['status'].startswith('200')
