from bson import ObjectId
from pymongo import MongoClient
import gridfs

from klar import App, HttpError
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
def upload(uploads, response, gfs):
    if 'avatar' in uploads:
        f = uploads['avatar']
        oid = gfs.put(f.file, filename=f.filename)
        return response.redirect('/files/%s' % oid)
    return 400

@app.get('/files/<id>')
def download(id:objectid, gfs):
    if gfs.exists(id):
        return gfs.get(id).read(), ('Content-Type', 'image/png')
    return 404

if '__main__' == __name__:
    app.run()
