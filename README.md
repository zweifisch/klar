# klar

```py
from klar import App

app = App()

@app.get('/hello/<name>')
def hello(name):
	return name

if __name__ == '__main__':
	app.run()
```

## type

*needs python3*

```py
@app.get('/add/<n>/<n2>')
def hello(n:int, n2:int):
	return n + n2
```

### custom type

```py
product = {
	"type": "object"
}

@app.post('/product')
def create(body: product):
	app.db.products.insert(body)
	return {"ok": True, "msg": "product created"}
	
@app.on(400)
def function(errors, request):
	# log(request.path, request.body)
	return errors
```

## restful

```py
from .resource import product, catalog

app = App()

app.resource(product, catalog)

if __name__ == '__main__':
	app.run()
```

resource/product.py

```py
from klar import transform
from .schemas import product

@transform
def filters(input):
	return {} if input not instanceof list
	input = (x.split(':') for x in input if 2 == len(x.split(':')))
	return dict(input)

def create(body: product, db):
	return db.products.insert(body)

def show(id: string):
	item = db.products.find_one_by_id(id)
	return item if item else 404

def list(shift: int, limit: int, filter: filters, db):
	criteria = map(filters, 
	products = db.products.find(filter).skip(shift).limit(shift)
```
