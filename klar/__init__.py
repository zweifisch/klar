from .klar import *
from .importers import JsonImporter
from .importers import HtmlImporter
from .importers import MustacheImporter
from .importers import install

install(JsonImporter(ext=".json"))
install(HtmlImporter(ext=".html"))
install(MustacheImporter(ext=".mustache"))
