
from klar import App, etag
from datetime import datetime

app = App()

start_time = datetime.utcnow()


@app.get('/')
def home():
    return 'home', ('Last-Modified', start_time)


@app.get('/test')
def test() -> etag:
    return 'test'
