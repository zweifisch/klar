# klar

a micro web framework built for fun

* argument annotation(so python3 is needed)
* jsonschema intergration

```py
from klar import App

app = App()

@app.get('/hello/<name>')
def hello(name: str, times: int = 1):
	return "hello " * times + name
```

run it using [wsgi-supervisor](https://github.com/zweifisch/wsgi-supervisor)

```sh
wsgi-supervisor app:app
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
def create(body: product, db):
	db.products.insert(body)
	return {"ok": True}
```

schemas can/should be imported from json or yaml(TBD) files

```
|--app.py
|--schemas.json
```

product in schema.json

```
{
	product: {...}
}
```

```python
from schemas import product

@app.post('/product')
def create(body: product):
	pass
```

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
import redis
app.provide('kv', (redis.Redis, {'host': 'localhost'}))
```

## rest(TBD)

```python
from resource import product, catalog

app = App()

app.resource(product, catalog, prefix="/v1")

if __name__ == '__main__':
	app.run()
```

in product

```python
from .schemas import product

def create(body: product, db):
	return db.products.insert(body)

def show(id: str):
	item = db.products.find_one_by_id(id)
	return item if item else 404

def list(shift: int, limit: int, db):
	products = db.products.find().skip(shift).limit(shift)
```

## event(TBD)

```python
@on(404)
def not_found(request):
	return 'not found'
```

## post processing(TBD)

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

## session

session depends on `cache`, but klar does't has it builtin

to use redis as session backend:

```python
import redis

@app.provide('cache')
def cache():
	return redis.Redis(host='localhost', port=6379, db=0)
```

or

```python
app.privide('cache', (redis.Redis, {'host': 'localhost'}))
```

### use session

```python
@app.post('/login')
def login(body, session):
	# check body.username and body.password
	if founduser:
		session.set('userid', userid)

@app.post('/login')
def logout(session):
	session.destroy()

@app.get('/admin')
def admin(session):
	if session.get('userid'):
		pass
```

## cookies

```python
cookies.get(key, default)
cookies.set(key, value)
cookies.delete(key)

cookies.set(key, value, httponly=True)
cookies.set_for_30_days(key, value)
```

## serving static files

should only be used in development enviroment

```
app.static('/public/')
```

```
app.static('/public/', 'path/to/public/dir')
```

