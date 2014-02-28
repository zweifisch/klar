from .klar import *
from .importers import JsonImporter
from .importers import TemplateImporter
from .importers import MustacheImporter
from .importers import install

install(JsonImporter(ext=".json"))
install(TemplateImporter(ext=".html"))
install(MustacheImporter(ext=".mustache"))
