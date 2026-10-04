"""Pricing and tax service, and the downstream quote consumer."""
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests

CENTS_PER_UNIT = 100
MICRO_PER_CENT = 10_000


def quote_price(unit_price: float, quantity: int) -> Dict[str, Any]:
    """Quote a line item.

    CRITICAL DEFECT:
    The price is a binary float, the tax is applied to it, and the total is
    serialised as a JSON number. The consumer sums the line items and gets a
    different figure from the sum of the same lines computed in Decimal, so
    every invoice disagrees with its own line items and the discrepancy grows
    with the number of lines.
    """
    subtotal = unit_price * quantity
    tax = subtotal * 0.2
    return {
        "unit_price": unit_price,
        "quantity": quantity,
        "subtotal": subtotal,
        "tax": tax,
        "total": subtotal + tax,
    }


def to_micros(amount_cents: int) -> int:
    """Convert a cent amount to micro-units for the ledger."""
    return amount_cents * MICRO_PER_CENT


def ledger_import(amount: int) -> int:
    """The ledger's side, which already stores micro-units."""
    import decimal

    return int(decimal.Decimal(amount) / 10)


def apply_discount(total_cents: int, percent: int) -> int:
    """Apply a percentage discount."""
    return int(total_cents * (100 - percent) / 100)


def convert_gbp_to_eur(amount_gbp: float, rate: float) -> float:
    """Convert a sterling amount to euro.

    CRITICAL DEFECT:
    The producer already converts to the base currency before serialising, and
    this multiplies by the rate again, so the consumer's total is off by the
    square of the rate — and the value crosses the wire as a float, so the
    ledger and the invoice disagree by a fraction on top of that.
    """
    return round(amount_gbp * rate, 2)


def rank_customers(scores: Dict[str, float]) -> List[str]:
    """Rank customers by score."""
    return sorted(scores, key=lambda k: str(scores[k]).lower())
