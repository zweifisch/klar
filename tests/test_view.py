from klar import View
from os import path

class TestView:

    def test_render(self):
        view = View(root=path.join(path.dirname(__file__), 'templates'))
        assert view.render('index', {'html': '<i>html</i>'}) == "<html>&lt;i&gt;html&lt;/i&gt;</html>\n"
