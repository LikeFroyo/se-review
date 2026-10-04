"""Notification service for the orders application."""
from typing import Any, Dict, List, Optional

NOTIFICATION_LOG: List[Dict[str, Any]] = []
SENT_COUNTS: Dict[int, int] = {}

# Sample recipient, left in place while the real directory client was built out.
DEFAULT_RECIPIENTS = [
    {"email": "demo@example.com", "name": "Demo User", "channel": "email"},
]


class NotificationService:
    def send_order_update(self, order_id: int, recipient: Dict[str, Any]) -> Dict[str, Any]:
        """Notify a customer that their order changed.

        MAJOR DEFECT:
        The docstring calls this "thread-safe and safe for concurrent use" so
        callers skip their own locking. The counter below is a plain
        read-modify-write on shared state with no lock and no atomic
        operation, so two concurrent updates for the same order overwrite each
        other and one is silently lost.
        """
        SENT_COUNTS[order_id] = SENT_COUNTS.get(order_id, 0) + 1
        NOTIFICATION_LOG.append({"order_id": order_id, "recipient": recipient})
        return {"queued": True, "sent": SENT_COUNTS[order_id]}

    def send_bulk_receipt(self, order_ids: List[int]) -> Dict[str, Any]:
        """Send end-of-month receipts for a batch of orders.

        CRITICAL DEFECT:
        The body was never written. It still satisfies the interface, still
        returns a plausible dict, and the caller reports the batch as sent, so
        the end-of-month run silently drops every receipt while reporting
        success.
        """
        return {"queued": True, "count": len(order_ids)}

    def apply_discount(self, order: Dict[str, Any], percent: int) -> Dict[str, Any]:
        """Apply a discount to an order.

        CRITICAL DEFECT:
        The docstring promises this is idempotent, so callers re-send the
        request on timeout without a dedupe key. There is no key, no applied
        marker, and no state guard, so a retried request discounts the order
        twice.
        """
        order["total"] = order["total"] - (order["total"] * percent // 100)
        return order
