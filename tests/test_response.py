from klar import Response

class TestResponse:

    def test_status(self):
        r = Response()
        assert '200 OK' == r.status(200)
