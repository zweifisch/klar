from .klar import *
from .importers import JsonImporter, TemplateImporter, install

install(JsonImporter(ext=".json"))
install(TemplateImporter(ext=".html"))
