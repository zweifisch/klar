import os
import sys
import imp
import re


class BaseImporter:
    def find_module(self, fullname, path):
        for dirname in sys.path:
            filename = os.path.join(dirname, *(fullname.split('.'))) + self.ext
            if os.path.exists(filename):
                self.filename = filename
                return self

    def load_module(self, fullname):
        if fullname in sys.modules:
            mod = sys.modules[fullname]
        else:
            sys.modules[fullname] = mod = imp.new_module(fullname)
        mod.__file__ = self.filename
        mod.__loader__ = self
        exec(self.get_source(self.filename), mod.__dict__)
        return mod


class JsonImporter(BaseImporter):
    def __init__(self, ext='.json'):
        self.ext = ext

    def get_source(self, filename):
        template = """
import json
root = json.loads(\"\"\"%s\"\"\")
locals().update(root)
"""
        return template % slurp(filename)


class TemplateImporter(BaseImporter):
    code_template = """
from cgi import escape
def %(fn)s(kvs):
    return \"\"\"%(template)s\"\"\" %% {k: escape(v) for k, v in kvs.items()}
"""

    def __init__(self, ext='.html'):
        self.ext = ext

    def get_source(self, filename):
        data = {
            "fn": basename(filename),
            "template": compile_template(slurp(filename))
        }
        return self.code_template % data


def slurp(filename):
    with open(filename) as fp:
        return fp.read()

def basename(filename):
    return os.path.splitext(os.path.basename(filename))[0]

def compile_template(src):
    return re.sub(r'<%\s*(\w+)\s*%>', '%(\\1)s', src)

def install(importer):
    return sys.meta_path.append(importer)

def uninstall(importer):
    sys.meta_path.remove(importer)
