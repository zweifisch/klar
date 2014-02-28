from .klar import *
from .importers import JsonImporter, YamlImporter
from .importers import SimpleTemplateImporter, MustacheImporter
from .importers import install

install(JsonImporter(ext=".json"))
install(YamlImporter(ext=".yaml"))
install(SimpleTemplateImporter(ext=".html"))
install(MustacheImporter(ext=".mustache"))
