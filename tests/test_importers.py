import klar


class TestImporters:

    def test_template_import(self):
        import templates.index
        expected = "<html>&lt;i&gt;html&lt;/i&gt;</html>\n"
        assert templates.index({'html': '<i>html</i>'}) == expected

    def test_json_import(self):
        from schemas import product
        assert product['type'] == 'object'
