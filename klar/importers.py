import os
import sys
import imp
import re
import types


class Finder:
    def __init__(self, ext):
        self.ext = ext

    def find_module(self, fullname, path):
        for dirname in sys.path:
            filename = os.path.join(dirname, *(fullname.split('.'))) + self.ext
            if os.path.exists(filename):
                self.filename = filename
                return self


class BaseImporter(Finder):
    def load_module(self, fullname):
        if fullname in sys.modules:
            mod = sys.modules[fullname]
        else:
            sys.modules[fullname] = mod = imp.new_module(fullname)
            mod.__file__ = self.filename
            mod.__loader__ = self
            exec(self.get_source(self.filename), mod.__dict__)
        return mod


class TemplateModule(types.ModuleType):
    def __call__(self, kvs=None):
        return self.__call__(kvs)


class TemplateImporter(Finder):
    def load_module(self, fullname):
        if fullname in sys.modules:
            mod = sys.modules[fullname]
        else:
            sys.modules[fullname] = mod = TemplateModule(fullname)
            mod.__file__ = self.filename
            mod.__loader__ = self
            exec(self.get_source(self.filename), mod.__dict__)
        return mod


class JsonImporter(BaseImporter):
    def get_source(self, filename):
        template = """
import json
root = json.loads(\"\"\"%s\"\"\")
locals().update(root)
"""
        return template % slurp(filename)


class SimpleTemplateImporter(TemplateImporter):
    code_template = """
from html import escape
from string import Template

template = Template(\"\"\"%s\"\"\")

def __call__(kvs=None):
    if type(kvs) is dict:
        return template.substitute({k: escape(v) for k, v in kvs.items()})
    else:
        return template.template"""

    def get_source(self, filename):
        return self.code_template % slurp(filename)


class JadeImporter(TemplateImporter):
    def get_source(self, filename):
        pass


class JinjaImporter(TemplateImporter):
    def get_source(self, filename):
        pass


class MustacheImporter(TemplateImporter):
    code_template = """
from pystache import render
def __call__(kvs=None):
    template = \"\"\"%s\"\"\"
    if type(kvs) is dict:
        return render(template, kvs)
    else:
        return template"""

    def get_source(self, filename):
        return self.code_template % slurp(filename)


def slurp(filename):
    with open(filename) as fp:
        return fp.read()


def basename(filename):
    return os.path.splitext(os.path.basename(filename))[0]


def install(importer):
    return sys.meta_path.append(importer)


def uninstall(importer):
    sys.meta_path.remove(importer)
