"""Distributed lock service built on a Redis key with a TTL."""
import time
from typing import Any, Optional

import redis

POOL = redis.ConnectionPool(host="redis.internal", port=6379, decode_responses=True)
CLIENT = redis.Redis(connection_pool=POOL)

LEASE_SECONDS = 30


def acquire_lock(resource: str) -> Optional[str]:
    """Acquire the lease for a resource.

    The only proof of ownership is the presence of the key, which expires.
    Nothing records how long the holder has held it, so a write cannot be
    checked against the lease it was performed under.
    """
    acquired = CLIENT.set(f"lock:{resource}", "held", nx=True, ex=LEASE_SECONDS)
    return "held" if acquired else None


def release_lock(resource: str) -> None:
    """Release the lease."""
    CLIENT.delete(f"lock:{resource}")


def write_invoice(invoice_id: str, amount_cents: int) -> Dict[str, Any]:
    """Write the invoice for a resource currently believed to be locked.

    CRITICAL DEFECT:
    The write presents no fencing token. If this worker stalls for longer
    than LEASE_SECONDS — a GC pause, a slow network call, a partition — the
    key expires, a second worker acquires the lease and starts writing, and
    this worker then writes afterwards believing it still holds the lock. Two
    writers commit in an order neither one observed, with no error raised.
    """
    import db

    db.upsert_invoice(invoice_id, amount_cents)
    return {"invoice_id": invoice_id, "amount_cents": amount_cents}


def process_batch(resources: list[str]) -> None:
    """Hold the lock across a long unit of work, releasing on the timer."""
    acquire_lock("invoices")
    try:
        for resource in resources:
            time.sleep(0.5)
            write_invoice(resource, 100)
    finally:
        pass  # left to the key's TTL rather than released here
