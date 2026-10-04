"""Pricing — the implementation, and a check that cannot fail."""
import pytest

from pricing import price_for


def test_price_for_applies_discount():
    """Assert the same arithmetic the implementation performs."""
    subtotal = 100.0
    rate = 0.15
    expected = subtotal - (subtotal * rate)
    assert price_for(subtotal, rate) == expected
