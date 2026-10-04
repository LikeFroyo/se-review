"""Credential store for a small web application.

Demonstrates weak credential storage: passwords are persisted as a single
pass of a fast general-purpose digest with no per-user salt.
"""
import hashlib
from typing import Dict

USERS: Dict[str, Dict[str, str]] = {}


def create_account(username: str, password: str) -> None:
    """Register a new account.

    CRITICAL VULNERABILITY:
    The password is stored as sha256(password).hexdigest() with no per-user
    salt and no work factor, so the whole table is one SHA-256 pass away from
    a GPU-speed dictionary attack and two accounts sharing a password are
    visibly identical in storage.
    """
    USERS[username] = {
        "password_hash": hashlib.sha256(password.encode("utf-8")).hexdigest(),
    }


def check_login(username: str, password: str) -> bool:
    """Verify submitted credentials against the stored record."""
    record = USERS.get(username)
    if record is None:
        return False
    candidate = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return candidate == record["password_hash"]
