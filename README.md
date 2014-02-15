# klar

a micro web framework built for fun

* argument annotation(so python3 is needed)
* jsonschema

```py
from klar import App

app = App()

@app.get('/hello/<name>')
def hello(name: str, times: int = 1):
	return "hello " * times + name

if __name__ == '__main__':
	app.run()
```

```sh
$ curl 'localhost:3000/hello/klar?times=2'
hello hello klar
```

## custom types using jsonschema

```python
product = {
	"type": "object"
	"properties": {
		"name": {
			"type": "string"
		},
		"price": {
			"type": "number"
		},
	},
	"additionalProperties": False,
}

@app.post('/product')
def create(body: product):
	app.db.products.insert(body)
	return {"ok": True}
```

schemas can/should be imported from json or yaml(TBD) files

```python
|--app.py
|--schemas
   |--product.json
```

@app.post('/product')
def create(body: product):
	app.db.products.insert(body)
	return {"ok": True}

## dependency injection

```python
@app.get('/admin')
def admin(session, response):
	if session.get('user_id') is None
		return response.redirect('/login')
```

useful ones:

* request
* session
* cookie

provide a custom dependency using decorator

```python
@app.provide('db')
def get_db_connection():
	conn = SomeDB(url="localhost:3349")
	return conn
```

a more scalable way

```python
from mysession import MySession
app.provide('session', (MySession, 'localhost:2343'))
```

## rest TBD

```python
from resource import product, catalog

app = App()

app.resource(product, catalog)

if __name__ == '__main__':
	app.run()
```

in product

```python
from .schemas import product

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

## event TBD

```python
@on(404)
def not_found(request): ->
	return 'not found'
```

## post processing

```python
def jsonp(body, headers, request):
	callback = request.params.get('callback')
	if callback:
		body = "%s(%s)" % (callback, json.dumps(body))
		headers["Content-Type"] = ["application/javascript"]
		return {"body": body, "heders", headers}

@app.get('/resource') -> jsonp:
	return {"key": "value"}
```

special argumants: `code`, `body`, `headers` return them in an dict to take
effect, all of them are optional

to use more than one processors

```python
@app.get('/resource') -> (jsonp, etags):
	return {"key": "value"}
```

## template rendering

```
|--app.py
|--templates
   |--home.html
```

```python
from template.home import tmpl_home

@app.get('/') -> tmpl_home :
	return {"key": "value"}
```

`tmpl_home` is a function that accecpts a single argument
it's basically equivalent to this:

```python
@app.get('/') -> tmpl_home :
	return tmpl_home({"key": "value"})
```
