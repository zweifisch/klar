from klar import App
from request import get, json_request, post
import json
import datetime

class TestApp:

    def test_hello(self):
        app = App()

        @app.get('/hello/<name>')
        def hello(name: str, times: int=1):
            return "hello " * times + name

        assert get(app, '/hello/klar', {"times": 2})['body'] == "hello hello klar"

    def test_routing(self):
        app = App()

        @app.get('/')
        def index():
            return 'index'

        @app.get('/foo')
        def index():
            return 'foo'

        assert get(app=app, path='/')['body'] == 'index'
        assert get(app=app, path='/foo')['body'] == 'foo'
        assert get(app=app, path='/bar')['status'].startswith('404')

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

        assert get(app=app, path='/test/200', query={"foo": 1})['body'] == '201'

    def test_template_rendering(self):
        app = App()

        from templates import tmpl_test

        @app.get('/test')
        def test(key) -> tmpl_test:
            return {"key": key}

        assert get(app, '/test', {"key": "foo"})['body'] == "key is foo\n"

    def test_cookie(self):

        app = App()

        @app.get('/test')
        def test(cookies):
            return cookies.get('id')

        @app.get('/test-set')
        def test(cookies):
            cookies.set('foo', 'bar')
            return ''

        @app.get('/test-expires')
        def test(cookies):
            cookies.set_for_30_days('foo', 'bar', httponly=True)
            return ''

        @app.get('/test-delete')
        def test(cookies):
            cookies.delete('id')
            return ''

        assert get(app, '/test', cookies={"id": "foo"})['body'] == "foo"

        expected = [('Content-Type', 'text/html; charset=utf-8'),
                    ('Set-Cookie', 'foo=bar')]
        res = get(app, '/test-set', cookies={"id": "foo"})
        assert res["status"] == "200 OK"
        assert res["headers"] == expected

        expires = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).strftime("%a, %d %b %Y %H:%M:%S GMT")
        expected = [('Content-Type', 'text/html; charset=utf-8'),
                    ('Set-Cookie', 'foo=bar; expires=%s; httponly' % expires)]
        assert get(app, '/test-expires', cookies={"id": "foo"})['headers'] == expected

        expires = datetime.datetime.utcfromtimestamp(0).strftime("%a, %d %b %Y %H:%M:%S GMT")
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

        res = post(app, '/login', {'username':'admin', 'passwd': 'secret'})
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
