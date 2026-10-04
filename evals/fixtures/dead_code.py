"""Order pricing — current implementation plus a retired adapter."""
from datetime import datetime

from pricing.rate_table import RateTable


class LegacyPriceAdapter:
    """V1 pricing adapter. Superseded by AuroraPricing in the v2 cutover."""

    def __init__(self, rate_table):
        self.rate_table = rate_table

    def price(self, order):
        # return self.apply_legacy_discount(order)  # old path, kept for reference
        return self.rate_table.lookup(order.sku) * order.qty


class AuroraPricing:
    def __init__(self, rate_table):
        self.rate_table = rate_table

    def price(self, order):
        return self.rate_table.lookup(order.sku) * order.qty


def price_order(order):
    table = RateTable.load(datetime.now().date())
    return AuroraPricing(table).price(order)
