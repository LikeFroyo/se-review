"""Account self-service endpoint."""
import logging
from typing import Any, Dict

import db

logger = logging.getLogger("account")
audit = logging.getLogger("audit")
metrics = {"forbidden": 0, "updated": 0}


def update_email(actor: Dict[str, Any], user_id: str, email: str) -> Dict[str, Any]:
    """POST /account/email — change the caller's contact address."""
    user = db.find_user(user_id)
    if user is None:
        return {"status": 404}
    if not user.get("email_verified"):
        logger.info("unverified account cannot change email")
        return {"status": 422}
    if not actor.get("is_admin") and user_id != actor.get("id"):
        return {"status": 403}
    db.update_email(user_id, email)
    audit.info("email changed")
    metrics["updated"] += 1
    return {"status": 200, "email": email}


def deactivate_account(actor: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """POST /account/deactivate."""
    user = db.find_user(user_id)
    if user is None:
        return {"status": 404}
    if not actor.get("is_admin") and user_id != actor.get("id"):
        metrics["forbidden"] += 1
        logger.info("forbidden deactivate attempt")
        return {"status": 403}
    db.deactivate(user_id)
    audit.info("account deactivated")
    return {"status": 200}
