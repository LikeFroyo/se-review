"""Checkout workflow spanning inventory, payments, and shipping services."""
from typing import Any, Dict, List, Optional

import requests

INVENTORY = "https://inventory.internal/v2"
PAYMENTS = "https://payments.internal/v2"
SHIPPING = "https://shipping.internal/v2"

SAGA_LOG: List[Dict[str, Any]] = []


def place_order(order_id: str, sku: str, qty: int, amount_cents: int) -> Optional[Dict[str, Any]]:
    """Reserve stock, charge the customer, then create a shipment.

    CRITICAL DEFECT:
    Each step commits on its own service and there is no saga, no
    compensating action, and no reconciler. If the shipping call fails after
    the charge has settled, the reservation is never released and the charge
    is never refunded. Nothing records that this order is half-complete, so
    the customer's money stays held against stock that will never ship and
    no process will ever find the pair again.
    """
    reservation = requests.post(
        f"{INVENTORY}/reservations", json={"sku": sku, "qty": qty}, timeout=10
    )
    if reservation.status_code != 201:
        return None
    SAGA_LOG.append({"order_id": order_id, "step": "reserved"})

    charge = requests.post(
        f"{PAYMENTS}/charges",
        json={"order_id": order_id, "amount_cents": amount_cents},
        timeout=10,
    )
    if charge.status_code != 201:
        # Stock is held and never released.
        return None
    SAGA_LOG.append({"order_id": order_id, "step": "charged"})

    shipment = requests.post(
        f"{SHIPPING}/shipments", json={"order_id": order_id, "sku": sku, "qty": qty}, timeout=10
    )
    if shipment.status_code != 201:
        # Charged, never shipped, never reconciled.
        return None
    SAGA_LOG.append({"order_id": order_id, "step": "shipped"})
    return {"order_id": order_id, "status": "placed"}
