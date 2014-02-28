
from klar import App
from schema import product

app = App()


@app.post('/')
def index(body: product):
    return body
