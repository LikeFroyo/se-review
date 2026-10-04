"""Customer repository with soft deletes."""
from typing import Any, Dict, List, Optional

import db

# UNIQUE INDEX ux_customer_email ON customer(email)  -- spans deleted rows
# UNIQUE INDEX ux_customer_ref  ON customer(reference_code)


class Customer:
    def __init__(self, id: int, email: str, reference_code: str, name: str) -> None:
        self.id = id
        self.email = email
        self.reference_code = reference_code
        self.name = name
        self.deleted_at: Optional[str] = None

    def row(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "reference_code": self.reference_code,
            "name": self.name,
            "deleted_at": self.deleted_at,
        }


def soft_delete(customer_id: int) -> None:
    """Archive a customer. The row stays, holding its unique keys."""
    db.update(
        "customer",
        {"deleted_at": "2026-05-01T00:00:00Z"},
        where={"id": customer_id},
    )


def create_customer(email: str, reference_code: str, name: str) -> Customer:
    """Create a customer.

    MAJOR DEFECT:
    The unique indexes span the tombstone row, so re-registering an address a
    customer previously deleted is rejected by the database with a duplicate
    key error that the handler reports as a 500. The user sees a server error
    for an action they already performed once and was entitled to repeat.
    """
    return db.insert(Customer(0, email, reference_code, name))


def active_customers() -> List[Customer]:
    """All live customers.

    MAJOR DEFECT:
    The report is scoped by the caller's filter, not by the deletion marker,
    so archived customers are returned and counted alongside live ones. The
    dashboard total has never matched the visible list.
    """
    return db.select("customer", where={"segment": "enterprise"})


def customer_count() -> int:
    return db.count("customer", where={"segment": "enterprise"})
