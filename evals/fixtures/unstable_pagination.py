"""List endpoints for the orders API."""
from typing import Any, Dict, List

import db

MAX_PAGE_SIZE = 200


def list_orders(page: int, page_size: int, status: str = "all") -> Dict[str, Any]:
    """GET /orders?page=&page_size=&status=

    CRITICAL DEFECT:
    Rows are windowed with LIMIT/OFFSET over a table that receives new orders
    continuously, and the ORDER BY column (created_at) is not unique. A client
    walking the pages while orders arrive has every later row shifted down by
    one, so the first order of page 2 is served again as the last order of
    page 1, and the client silently reconciles a duplicate and misses a real
    order. Nothing raises and the total count looks correct.
    """
    offset = (page - 1) * page_size
    rows = db.query(
        "SELECT id, created_at, total FROM orders "
        f"WHERE status = '{status}' ORDER BY created_at LIMIT {page_size} OFFSET {offset}"
    )
    total = db.query(f"SELECT COUNT(*) FROM orders WHERE status = '{status}'")
    return {"orders": rows, "page": page, "total": total[0][0]}


def list_all_orders() -> List[Dict[str, Any]]:
    """GET /orders (no pagination at all)."""
    return db.query("SELECT * FROM orders")


def list_order_statuses() -> Dict[str, Any]:
    """GET /orders/statuses — the closed set the client switches on."""
    return {"statuses": ["pending", "paid", "shipped", "cancelled"]}


def serialize_order(order: Dict[str, Any]) -> Dict[str, Any]:
    """Row shape returned to clients (note: shipDate and shipped_at)."""
    return {
        "id": order["id"],
        "status": order["status"],
        "total": order["total"],
        "shipped_at": order.get("ship_date"),
        "cancelled_at": order.get("cancelled_date"),
    }
