from klar import Response, get_status

class TestResponse:

    def test_status(self):
        assert '200 OK' == get_status(200)

    def test_redirect(self):
        response = Response()
        assert (301, ('Location', '/')) == response.redirect('/', permanent=True)
