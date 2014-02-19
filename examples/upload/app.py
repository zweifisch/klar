from bson import ObjectId
from pymongo import MongoClient
import gridfs

from klar import App, HttpError, redirect
from upload import tmpl_upload

app = App()

def objectid(id):
    try:
        return ObjectId(id)
    except:
        raise HttpError(404, 'file not found')

@app.provide('gfs')
def gfs_privider():
    db = MongoClient().test
    return gridfs.GridFS(db)

@app.get('/')
def home() -> tmpl_upload:
    pass

@app.post('/upload')
def upload(uploads, gfs):
    if 'avatar' in uploads:
        f = uploads['avatar']
        oid = gfs.put(f.file, filename=f.filename, content_type=f.type)
        return redirect('/files/%s' % oid)
    return 400

@app.get('/files/<id>')
def download(id: objectid, gfs):
    if gfs.exists(id):
        f = gfs.get(id)
        return f.read(), ('Content-Type', f.content_type)
    return 404
