import pytest
from klar import *

def test_invoke():

    def fn(foo, bar):
        return (foo, bar)

    assert invoke(fn, {'bar':'bar'}, {'foo': 'foo'}) == ('foo', 'bar')

    assert invoke(fn, {'bar':'bar', 'foo': 'foo'}) == ('foo', 'bar')

    with pytest.raises(Exception):
        invoke(fn, {'foo': 'foo'})

    with pytest.raises(Exception):
        invoke(fn, {})

    class Foo:
        def __init__(self, foo, bar):
            self.foo = foo
            self.bar = bar

    foo = invoke(Foo, {'bar':'bar'}, {'foo': 'foo'})
    assert foo.foo == 'foo'
    assert foo.bar == 'bar'

