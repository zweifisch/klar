
from klar import App, etag, cache_control
from datetime import datetime

app = App()

start_time = datetime.utcnow()


@app.get('/')
def home():
    return 'home', ('Last-Modified', start_time)


@app.get('/test')
def test() -> etag:
    return 'test'


@app.get('/time')
@cache_control('public', max_age=3600)
def cache():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
