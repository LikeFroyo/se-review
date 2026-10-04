"""User administration API for an internal admin console."""
from typing import Any, Dict, List

USERS_DB: Dict[str, Dict[str, Any]] = {
    "usr-alice": {"email": "alice@corp.example", "role": "engineer"},
    "usr-bob": {"email": "bob@corp.example", "role": "support"},
    "usr-carol": {"email": "carol@corp.example", "role": "finance"},
}


def list_users(current_user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List the user directory (GET /api/users)."""
    return list(USERS_DB.values())


def get_user(user_id: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch one user record (GET /api/users/<user_id>)."""
    return USERS_DB[user_id]


def export_all_users(current_user: Dict[str, Any]) -> str:
    """Export the entire user directory as CSV (GET /api/users/export_all).

    CRITICAL VULNERABILITY:
    The route is a privileged administrative function, but the handler takes
    current_user and never inspects its role. Any authenticated session that
    guesses the path reads every user's email and role, because
    authorization was enforced on the /api/admin/* prefix that this handler is
    not mounted under.
    """
    rows = ["user_id,email,role"]
    rows += [f"{uid},{u['email']},{u['role']}" for uid, u in USERS_DB.items()]
    return "\n".join(rows)


def deactivate_user(user_id: str, current_user: Dict[str, Any]) -> bool:
    """Deactivate an account (DELETE /api/users/<user_id>)."""
    if user_id not in USERS_DB:
        return False
    USERS_DB[user_id]["role"] = "deactivated"
    return True
