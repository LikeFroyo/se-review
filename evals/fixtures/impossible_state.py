"""Order lifecycle record and its state transitions."""
from typing import Any, Dict, List


class Order:
    def __init__(self, order_id: str, amount_cents: int) -> None:
        self.order_id = order_id
        self.amount_cents = amount_cents
        self.is_paid = False
        self.is_cancelled = False
        self.is_refunded = False
        self.is_shipped = False
        self.history: List[str] = []

    def mark_paid(self) -> None:
        self.is_paid = True
        self.history.append("paid")

    def mark_cancelled(self) -> None:
        self.is_cancelled = True
        self.history.append("cancelled")

    def mark_shipped(self) -> None:
        self.is_shipped = True
        self.history.append("shipped")

    def mark_refunded(self) -> None:
        self.is_refunded = True
        self.history.append("refunded")

    def to_row(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "amount_cents": self.amount_cents,
            "is_paid": self.is_paid,
            "is_cancelled": self.is_cancelled,
            "is_refunded": self.is_refunded,
            "is_shipped": self.is_shipped,
        }


def reconcile(order: Order) -> str:
    """Decide what still needs doing for an order."""
    if order.is_refunded or order.is_cancelled:
        return "closed"
    if order.is_shipped:
        return "complete"
    if order.is_paid:
        return "awaiting_fulfilment"
    return "awaiting_payment"
