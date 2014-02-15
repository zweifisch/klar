import klar

class TestImporters:

    def test_template_import(self):
        from templates import tmpl_index
        assert tmpl_index({'html': '<i>html</i>'}) == "<html>&lt;i&gt;html&lt;/i&gt;</html>\n"

    def test_json_import(self):
        from schemas import product
        assert product['type'] == 'object'
