from .klar import *
from .importers import JsonImporter
from .importers import SimpleTemplateImporter
from .importers import MustacheImporter
from .importers import install

install(JsonImporter(ext=".json"))
install(SimpleTemplateImporter(ext=".html"))
install(MustacheImporter(ext=".mustache"))
