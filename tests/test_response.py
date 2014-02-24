from klar import redirect, get_status

class TestResponse:

    def test_status(self):
        assert '200 OK' == get_status(200)

    def test_redirect(self):
        assert (301, ('Location', '/')) == redirect('/', permanent=True)
