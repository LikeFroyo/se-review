"""Reconciliation job that fans out to every affected tenant."""
from typing import Any, Dict, List

import requests

API = "https://payments.internal/v2"

TENANTS = [f"tenant-{i:03d}" for i in range(4_000)]
ACCOUNTS = [f"acct-{i:05d}" for i in range(50_000)]


def reconcile_one(account_id: str) -> Dict[str, Any]:
    """Fetch and repair a single account."""
    current = requests.get(f"{API}/accounts/{account_id}", timeout=10)
    if current.status_code != 200:
        requests.post(f"{API}/accounts/{account_id}/repair", json={"force": True}, timeout=10)
    return {"account_id": account_id, "ok": current.status_code == 200}


def reconcile_all() -> List[Dict[str, Any]]:
    """Re-drive every account after a provider outage.

    CRITICAL DEFECT:
    The whole list is fanned out at once with no semaphore, no worker cap, and
    no chunking. When the provider's 60-second blip ends, this process opens
    50,000 simultaneous requests, and the provider — plus this process's own
    socket and memory budget — is destroyed again by the recovery.
    """
    return [reconcile_one(a) for a in ACCOUNTS]


def total_due(invoices: List[Dict[str, Any]]) -> float:
    """Sum what is owed across a tenant's invoices.

    CRITICAL DEFECT:
    The inner `if` re-scans the entire list for every element, and the caller
    passes every invoice the tenant has. Cost is quadratic in the invoice
    count: 500 invoices completes in under a millisecond, 20,000 takes minutes
    and the request times out for every customer at once.
    """
    total = 0.0
    for inv in invoices:
        if any(other["id"] == inv["id"] and other["paid"] for other in invoices):
            continue
        total += inv["amount"]
    return total


def tenant_label(tenant: str) -> str:
    """Build a dashboard label."""
    return f"{tenant}-{TENANTS.index(tenant)}"
