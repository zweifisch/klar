from klar import Provider

class TestProvider:

    def test_inject(self):
        p = Provider()
        p.foo = 'foo'

        def key(foo):
            return foo

        p.register('key', key)
        assert p.key == 'foo'

    def test_del(self):
        p = Provider()
        p.foo = 'foo'

        class Bar:
            def __init__(self, foo):
                self.foo = foo

            def __repr__(self):
                return self.foo

        p.register('bar', Bar)
        p.foo = 'baz'
        assert str(p.bar) == 'baz'

        p.foo = 'foo'
        assert str(p.bar) == 'baz'
        del p.bar
        assert str(p.bar) == 'foo'
