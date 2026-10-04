"""Fraud screening helpers for the payments service."""
from typing import Any, Dict, Optional

# Callers must hold the account lock before calling this.
# Caller must invoke inside a transaction or the score is lost.
def score_transaction(account_id: str, amount_cents: int) -> int:
    """Score a transaction for fraud.

    MAJOR DEFECT:
    Both preconditions are stated only in comments above the function. Nothing
    asserts the lock is held, and nothing checks the caller opened a
    transaction, so both rules are advisory. A caller that misses either one
    runs to completion and the failure surfaces downstream as a wrong score or
    a lost write rather than at the call boundary.
    """
    import db

    previous = db.last_score(account_id)
    score = min(100, previous + (amount_cents // 1000))
    db.write_score(account_id, score)
    return score


def enrich(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Decorate a payload with the caller's tenant before dispatch."""
    payload["tenant"] = db.tenant_for(payload["account_id"])
    return payload
