# klar

a micro web framework built for fun

* argument annotation
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

schemas can and should be imported from json or yaml files

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

provide a custom dependency using decorator

```python
@app.provide('db')
def get_db_connection():
	conn = SomeDB(url="localhost:3349")
	return conn

import redis
app.provide('cache', (redis.Redis, {'host': 'localhost'}))
```

using `db` and `cache` in request handler

```python
@get('/article/<article_id>')
def get_article(article_id:int, db, cache):
    pass
```

predefined components:

* request
* session
* cookie
* router

## rest

```python
from resource import product, catalog

app = App()

app.resources(product, catalog, prefix="/v1")

if __name__ == '__main__':
	app.run()
```

in product

```python
from schema import product

# curl -X POST $host/v1/product -d @body
def create(body: product, db):
	return db.products.insert(body)

# curl $host/v1/product/$id
def show(product_id: str):
	item = db.products.find_one({_id: product_id})
	return item if item else 404

# curl $host/v1/product?shift=10&limit=10
def query(shift: int, limit: int, db):
	return db.products.find().skip(shift).limit(shift)

# curl -X PATCH $host/v1/product/$id -d @body
def modify(body: product, product_id: str):
	return db.products.update({_id: product_id}, {'$set': body})

# curl -X PUT $host/v1/product/$id -d @body
def replace(body: product, product_id: str):
	return db.products.update({_id: product_id}, body)

# curl -X DELETE $host/v1/product/$id
def destroy(product_id: str):
	return db.products.delete({_id: product_id})
```

### custom method

```python
from klar import method

@method('patch')  # default is GET
def like(product_id):
	return db.products.update({_id: product_id}, {'$inc': {'likes': 1}})

# curl -X PATCH $host/v1/product/$id/like
```

## events

listening for an event

```python
@on(404)
def not_found(request):
	print('%s not found' % request.path)
```

### custom events

```python
@on('user-login')
def onlogin(userid, db):
	print('user: %s logged in' % userid)
	db.users.update({_id:userid}, {'$inc': {'logincount': 1}})
```

emit an event

```python
def login(emitter):
	emitter.emit('user-login', userid=id)
```

## post processing

```python
# special params: body, code, headers
def jsonp(body, request):
    callback = request.query.get('callback')
    if callback:
        body = "%s(%s)" % (callback, json.dumps(body))
        return body, ("Content-Type", "application/javascript")

@app.get('/resource') -> jsonp:
	return {"key": "value"}
```

more than one processors:

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
import templates.home

@app.get('/') -> templates.home:
	return {"key": "value"}
```

`templates.home` accecpts an optional dict as argument
it's basically equivalent to this:

```python
@app.get('/'):
	return templates.home({"key": "value"})
```

### mustache

depends on pystache, `pip install pystache`

use `.mustache` as extension

```
|--templates
   |--home.mustache
```

```python
import templates.home
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

## config

config file path will be read from enviroment variable `$CONFIG`

if it's empty config.py will be loaded

config.py

```python
mongo = {
    "host": "127.0.0.1"
    "port": 27017
}
```

```python
from pymongo import MongoClient

@app.provide('db')
def db(config):
    return MongoClient(**config.mongo)
```

## reversed routing

```python
@app.get('user/<id>')
def user(id:str):
    pass
```

get a link to previous handler

```
def another_handler(router):
    href = router.path_for('user', id=3221)
```

## custom json encoder

```python
from bson.objectid import ObjectId

@app.json_encode(ObjectId)
def encode_objectid(obj):
    return str(obj)
```

by default `Iterable` is converted to `list`

