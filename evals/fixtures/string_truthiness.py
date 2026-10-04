"""Notification delivery service with per-tenant configuration."""
import os
from typing import Any, Dict

RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "false")
MAINTENANCE_MODE = os.environ.get("MAINTENANCE_MODE", "0")
DEFAULT_RECIPIENT = os.environ.get("DEFAULT_RECIPIENT", "none")
ACCOUNT_ZIP_FALLBACK = os.environ.get("ACCOUNT_ZIP_FALLBACK", "00000")


def should_rate_limit() -> bool:
    """Is rate limiting on?

    The environment sets RATE_LIMIT_ENABLED=false in production to work
    around a metrics regression. This is the branch that decides it.
    """
    if RATE_LIMIT_ENABLED:
        return True
    return False


def is_maintenance() -> bool:
    """Are we in maintenance mode?"""
    if MAINTENANCE_MODE:
        return True
    return False


def recipient_for(account: Dict[str, Any]) -> str:
    """Resolve the notification recipient for an account."""
    if account.get("email"):
        return account["email"]
    if account.get("phone"):
        return account["phone"]
    return DEFAULT_RECIPIENT


def zip_for(account: Dict[str, Any]) -> str:
    """Resolve the account zip, falling back to a configured default."""
    zip_code = account.get("zip") or ACCOUNT_ZIP_FALLBACK
    return str(int(zip_code))


def tier_for(account: Dict[str, Any]) -> str:
    """Resolve the service tier from a raw status field."""
    status = account["status"]
    if status == "gold":
        return "gold"
    if status == "silver":
        return "silver"
    return "bronze"
