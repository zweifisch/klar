from klar import Router


class TestRouter:

    def test_dispatch(self):
        router = Router()
        router.add_rule('GET', '/', 'handler4')
        router.add_rule('GET', '/path', 'handler')
        router.add_rule('POST', '/path', 'handler2')
        router.add_rule('GET', '/error', 'handler3')
        handler, params = router.dispatch('GET', '/path')
        assert params == {}
        assert handler == 'handler'
        handler, params = router.dispatch('POST', '/path')
        assert params == {}
        assert handler == 'handler2'
        handler, params = router.dispatch('GET', '/error')
        assert params == {}
        assert handler == 'handler3'
        handler, params = router.dispatch('DELETE', '/path')
        assert params is None
        assert handler is None

    def test_dispatch_with_params(self):
        router = Router()
        router.add_rule('GET', '/res/<key>:<value>', 'handler')
        handler, params = router.dispatch('GET', '/res')
        assert params is None
        assert handler is None
        handler, params = router.dispatch('GET', '/res/key:')
        assert params is None
        assert handler is None
        handler, params = router.dispatch('GET', '/res/_k1:=v1')
        assert params == {"key": "_k1", "value": "=v1"}
        assert handler == 'handler'

    def test_reverse(self):
        router = Router()
        router.add_rule('GET', '/avatar/<id>.<ext>', 'handler')
        url = router.path_for('handler', id=13132, ext="png")
        assert '/avatar/13132.png' == url
