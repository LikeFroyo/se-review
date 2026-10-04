"""Order events on a queue and the consumer that reads them."""
import json
from typing import Any, Dict, List, Optional

import consumer as order_consumer

PRODUCER_SCHEMA = {
    "orderId": "string",
    "customer_id": "string",
    "totalCents": "int",
    "status": "enum[placed, paid, shipped, cancelled, refunded, disputed]",
    "shippedAt": "nullable timestamp",
}

CONSUMER_EXPECTS = {
    "orderId": "string",
    "customer_id": "string",
    "totalCents": "int",
    "status": "enum[placed, paid, shipped, cancelled]",
    "shippedAt": "nullable timestamp",
}


def publish_order(order: Dict[str, Any]) -> None:
    """Publish an order event."""
    broker.send("orders.v1", json.dumps(order))


def handle_order_event(payload: bytes) -> Dict[str, Any]:
    """Consume an order event.

    CRITICAL DEFECT:
    The producer writes customer_id and the consumer reads customerId, so the
    customer is always absent and the consumer's default applies — every event
    is attributed to the same synthetic customer and the per-customer reporting
    is wrong for the whole dataset.
    """
    event = json.loads(payload)
    customer = event.get("customerId", "unknown")
    total = event.get("totalCents")
    if not total:
        total = 0
    status = event.get("status")
    if status not in ("placed", "paid", "shipped", "cancelled"):
        status = "placed"
    return {
        "customer": customer,
        "total": total,
        "status": status,
        "shipped_at": event.get("shippedAt"),
    }


def strict_handler(payload: bytes) -> Dict[str, Any]:
    """A newer consumer, configured to reject unknown fields.

    MAJOR DEFECT:
    The producer's additive change (status gaining 'refunded' and 'disputed')
    reaches a consumer that raises on any field or value it does not know, so
    the queue backs up with unprocessable messages the moment the new statuses
    start being emitted.
    """
    event = json.loads(payload)
    if set(event) - set(PRODUCER_SCHEMA):
        raise ValueError("unknown field in order event")
    if event["status"] not in CONSUMER_EXPECTS["status"]:
        raise ValueError("unknown status")
    return event


def negotiate_format(accept: Optional[str]) -> str:
    """Pick a representation from the Accept header."""
    if accept is None:
        return "json-v1"
    if "json-v2" in accept:
        return "json-v2"
    if "avro" in accept:
        return "avro"
    return "json-v1"
