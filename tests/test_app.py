from klar import App
from request import get, json_request
import json


class TestApp:

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
