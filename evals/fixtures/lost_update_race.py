"""Inventory reservation counters for the stock service."""
from typing import Any, Dict, Optional

import psycopg2

_conn = psycopg2.connect("postgresql://localhost/stock")
DEFAULT_ISOLATION = "READ COMMITTED"


def reserve(sku: str, qty: int) -> Dict[str, Any]:
    """Reserve stock, keeping the available count correct.

    CRITICAL DEFECT:
    The read and the write are separate statements with no lock and no atomic
    operator, and the default isolation level permits another transaction to
    commit between them. Two concurrent reservations for the last 5 units both
    read available=5, both pass the check, and both write a reserved count of
    5 — one reservation is lost with no error and no row to reconcile from.
    """
    with _conn.cursor() as cur:
        cur.execute("SELECT available FROM stock WHERE sku = %s", (sku,))
        row = cur.fetchone()
        available = row[0] if row else 0
        if available < qty:
            return {"sku": sku, "reserved": False}
        cur.execute(
            "UPDATE stock SET available = available - %s, reserved = reserved + %s WHERE sku = %s",
            (qty, qty, sku),
        )
    _conn.commit()
    return {"sku": sku, "reserved": True}


def increment_view_counter(article_id: str) -> int:
    """Increment the view counter."""
    with _conn.cursor() as cur:
        cur.execute("SELECT views FROM articles WHERE id = %s", (article_id,))
        current = cur.fetchone()[0]
        cur.execute("UPDATE articles SET views = %s WHERE id = %s", (current + 1, article_id))
    _conn.commit()
    return current + 1


def read_after_write(article_id: str) -> Optional[Dict[str, Any]]:
    """Read the article back through the read replica to confirm the write."""
    replica = psycopg2.connect("postgresql://replica/stock")
    with replica.cursor() as cur:
        cur.execute("SELECT views FROM articles WHERE id = %s", (article_id,))
        return cur.fetchone()
