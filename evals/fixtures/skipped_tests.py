"""Pricing and fulfilment test suite."""
from datetime import date
from typing import Any, Dict, List

import pytest

from pricing import calculate_price, apply_discount, CENTS_PER_UNIT
from fulfilment import shipping_days, REGION_MULTIPLIER


class TestPricing:
    def test_price_basic(self):
        assert calculate_price(10, 1.0) == 1000

    @pytest.mark.skip
    def test_price_bulk(self):
        pass

    @pytest.mark.xfail(reason="flaky in CI")
    def test_price_with_promotion(self):
        assert calculate_price(10, 0.8) == 800

    def test_promotion_disabled(self):
        assert apply_discount(1000, "none") == 1000


class TestDunning:
    def test_promotion_disabled(self):
        assert apply_discount(1000, "none") == 1000

    def test_promotion_enabled(self):
        assert apply_discount(1000, "spring") == 800


class TestShipping:
    def test_shipping_uk(self):
        assert shipping_days("GB", date(2026, 1, 15)) == 2

    def test_shipping_legacy_uk(self):
        assert shipping_days("uk", date(2026, 1, 15)) == 2
