from klar import TemplateImporter, JsonImporter, install

class TestImporters:

    def test_template_import(self):
        install(TemplateImporter(ext=".html"))
        from templates import index
        assert index({'html': '<i>html</i>'}) == "<html>&lt;i&gt;html&lt;/i&gt;</html>\n"

    def test_json_import(self):
        install(JsonImporter(ext=".json"))
        from schemas import product
        assert product['type'] == 'object'
