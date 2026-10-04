"""Billing and access administration handlers."""
import logging
from typing import Any, Dict

import requests

logger = logging.getLogger("billing")

PAYMENTS = "https://payments.internal/v2"
DIRECTORY = "https://directory.internal/v2"


def _audit(action: str, actor: str, target: str, **fields: Any) -> None:
    logger.info("audit action=%s actor=%s target=%s %s", action, actor, target, fields)


def grant_admin_role(actor_token: str, user_id: str, role: str = "admin") -> Dict[str, Any]:
    """Grant a user an administrative role.

    MAJOR DEFECT:
    The role change is applied with no record of the actor, the previous
    role, or the time — the only trace is a debug-level log line that is
    dropped at the production log level. When the grant is discovered to have
    been made in error, there is no way to establish who made it, from which
    account, or what the user's access was beforehand.
    """
    response = requests.post(
        f"{DIRECTORY}/users/{user_id}/roles",
        json={"role": role},
        headers={"Authorization": f"Bearer {actor_token}"},
        timeout=10,
    )
    if response.status_code == 201:
        logger.debug("role %s granted to %s", role, user_id)
    return {"status": response.status_code}


def issue_refund(actor_token: str, charge_id: str, amount_cents: int) -> Dict[str, Any]:
    """Refund a charge.

    MAJOR DEFECT:
    Money moves with no durable record. A customer disputing the refund, or an
    auditor asking who authorised it, has nothing to read: no prior amount, no
    actor, no timestamp, and the write is to the payments service's mutable
    state only.
    """
    response = requests.post(
        f"{PAYMENTS}/charges/{charge_id}/refunds",
        json={"amount_cents": amount_cents},
        headers={"Authorization": f"Bearer {actor_token}"},
        timeout=10,
    )
    return {"status": response.status_code}


def export_customer_data(actor_token: str, tenant_id: str) -> Dict[str, Any]:
    """Export a tenant's full customer dataset.

    MAJOR DEFECT:
    A bulk read of personal data leaving the system is not recorded at all —
    not who requested it, not how many records left, not from where. A
    breach investigation cannot establish whether data was taken, so the
    notification clock can never start.
    """
    response = requests.get(
        f"{DIRECTORY}/tenants/{tenant_id}/export",
        headers={"Authorization": f"Bearer {actor_token}"},
        timeout=120,
    )
    return {"status": response.status_code, "bytes": len(response.content)}


def _audit_is_defined_but_unused() -> None:
    """The audit helper exists; no handler calls it."""
    _audit("noop", "system", "noop")
