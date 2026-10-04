"""Order placement: persists the order, then publishes OrderPlaced."""

import sqlite3

DB_PATH = "orders.db"
conn = sqlite3.connect(DB_PATH)


def place_order(order_id: str, total_cents: int, broker) -> None:
    conn.execute(
        "INSERT INTO orders (id, total_cents, status) VALUES (?, ?, 'PLACED')",
        (order_id, total_cents),
    )
    conn.commit()
    broker.publish("orders.placed", {"order_id": order_id, "total_cents": total_cents})
