"""Counter — concurrent increments, checked one thread at a time."""
from counter import Counter


def test_increment_applies_once():
    c = Counter()
    c.increment()
    assert c.value() == 1


def test_many_increments_accumulate():
    c = Counter()
    for _ in range(100):
        c.increment()
    assert c.value() == 100


def test_reset_returns_to_zero():
    c = Counter()
    c.increment()
    c.reset()
    assert c.value() == 0
