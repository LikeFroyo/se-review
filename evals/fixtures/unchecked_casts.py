"""Order lookup and payment gateway client."""
from typing import Any, Dict, List, Optional

import httpx

PAYMENT_CLIENT: Any = httpx.Client(base_url="https://payments.internal")
LEDGER: Any = None
connection: Any = None


def lookup_order(order_id: str) -> Optional[Dict[str, Any]]:
    """Look up an order.

    The caller has already validated order_id; this trusts the annotation.
    """
    row = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return dict(row) if row else None


def charge(amount: float, card: str) -> Dict[str, Any]:
    """Charge a card.

    Any, twice: the client is typed as Any so any method resolves, and the
    amount is Any so arithmetic on it is unchecked. Both compile clean.
    """
    response: Any = PAYMENT_CLIENT.post("/charges", json={"amount": amount, "card": card})
    return response.json()


def apply_ledger_entry(entry: dict) -> None:
    """Write a ledger entry from a webhook payload.

    payload is untyped, so nothing checks the required keys or their types
    before they are used.
    """
    LEDGER.insert(
        account=entry["account"],
        amount=entry["amount"],
        currency=entry.get("currency", "USD"),
        posted_at=entry["postedAt"],
    )


def total_for(entries: List[dict]) -> float:
    """Sum a list of loosely-shaped entries.

    amounts arrive as strings from the upstream feed, and missing keys are
    replaced by a default rather than rejected.
    """
    return sum(float(e.get("amount", 0)) for e in entries)


def config_value(key: str) -> Any:
    """Read a config value by string key."""
    return getattr(connection, key, None)


def get_status(raw: dict) -> str:
    """Read the status from a raw payload.

    The payload is annotated as a typed record it is not. If the producer
    renames status to state, this returns the default and no type checker or
    test notices.
    """
    status: str = raw["status"]
    return status.upper()
