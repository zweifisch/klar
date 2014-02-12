
from klar import App
# from .schema import product

app = App()

@app.get('/')
def home():
    return 'home'

@app.get('/hello/<name>')
def hello(name):
    return "hello %s" % name

@app.get('/json')
def json():
    return {'ok': True}

@app.get('/add/<n>/<n2>')
def json(n:int, n2:int):
    return {"result": n + n2}

# @app.post('/product')
# def create_product(body: product):
#     return {product: product}

if '__main__' == __name__:
    app.run()
