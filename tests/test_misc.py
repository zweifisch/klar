
from klar import cached_property


class Lazy:
    _count = 0

    @cached_property
    def count(self):
        self._count += 1
        return self._count


def test_cached_property():
    l = Lazy()
    assert l.count == 1
    assert l.count == 1
