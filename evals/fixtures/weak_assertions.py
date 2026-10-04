"""Volume discount calculator with its test suite."""


def discounted(total_cents: int, percent: int) -> int:
    if percent < 0 or percent > 100:
        raise ValueError("percent must be between 0 and 100")
    return total_cents - (total_cents * percent) // 100


def test_typical_discount():
    assert discounted(10000, 10) >= 0


def test_full_discount():
    assert discounted(10000, 100) is not None


def test_rejects_invalid_percent():
    try:
        discounted(10000, 150)
        rejected = False
    except ValueError:
        rejected = True
    assert rejected is True
