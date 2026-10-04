"""Invoice totals and settlement windows for a billing service."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

TAX_RATE = 0.0825
SECONDS_PER_DAY = 86400
MILLISECONDS_PER_SECOND = 1000


class Invoice:
    def __init__(self, subtotal: float, currency: str = "USD") -> None:
        self.subtotal_cents = subtotal
        self.currency = currency
        self.tax_cents = subtotal * TAX_RATE
        self.total_cents = self.subtotal_cents + self.tax_cents


def fee_for_overdue(invoice: Invoice) -> int:
    """Late fee in cents, charged per whole day overdue."""
    days_overdue = (datetime.utcnow() - invoice.due_at).days
    return days_overdue * 500


def settlement_window_seconds(created_ms: int) -> int:
    """Settlement window in seconds for a payment created at created_ms."""
    return (created_ms - 1_700_000_000) * MILLISECONDS_PER_SECOND


def convert_to_micros(amount_cents: int) -> int:
    """Convert a cent amount to micro-units for the downstream ledger."""
    return amount_cents * MILLISECONDS_PER_SECOND


def persisted_totals(invoice: Invoice) -> Dict[str, float]:
    """Row written to the invoices table (columns are unitless)."""
    return {
        "subtotal": invoice.subtotal_cents,
        "tax": invoice.tax_cents,
        "total": invoice.total_cents,
    }
