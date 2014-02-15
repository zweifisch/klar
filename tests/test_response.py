# from klar import Response
from klar import get_status

class TestResponse:

    def test_status(self):
        assert '200 OK' == get_status(200)
