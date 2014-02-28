
from klar import App

import templates.html
import templates.mustache

app = App()


@app.get('/hello.html')
def html(name: str) -> templates.html:
    return {"name": name}


@app.get('/hello.mustache')
def mustache(name: str) -> templates.mustache:
    return {"name": name}
