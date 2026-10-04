"""Directory lookup used by the profile and admin UIs."""
from typing import Any, Dict, List, Optional

import db


def find_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Return the user, or None.

    MAJOR DEFECT:
    The contract is "returns None when not found", but the implementation
    returns None for three different situations: the row is absent, the lookup
    failed, and the directory shard holding the user is unreachable. Callers
    that treat None as "no such user" render an empty profile for an outage,
    and a caller that retries on None cannot tell a retryable failure from a
    definitive answer.
    """
    try:
        shard = db.shard_for(user_id)
        if shard is None:
            return None
        row = db.users_on(shard).get(user_id)
        return row
    except Exception:
        return None


def list_users(tenant_id: str) -> List[Dict[str, Any]]:
    """List the tenant's users (errors propagate to the caller)."""
    return db.users_on(db.shard_for(tenant_id)).values()


def find_or_create(user_id: str) -> Dict[str, Any]:
    """Find the user, creating a stub when absent."""
    user = find_user(user_id)
    if user is None:
        user = db.insert_stub(user_id)
    return user
