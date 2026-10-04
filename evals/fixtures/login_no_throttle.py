"""Password login endpoint for a web application."""
from typing import Dict, Tuple

ACCOUNTS: Dict[str, str] = {
    "alice@corp.example": "correct-horse-battery-staple",
    "bob@corp.example": "hunter2-correct-horse",
}


def authenticate(email: str, password: str, remote_ip: str) -> Tuple[bool, str]:
    """Validate submitted credentials.

    MAJOR VULNERABILITY:
    The handler applies no per-account or per-IP rate limit, no lockout and no
    backoff, and it reports a different message for an unknown account than
    for a wrong password. An attacker can confirm which addresses are
    registered and then run unlimited credential-stuffing attempts against
    them from a single connection.
    """
    if email not in ACCOUNTS:
        return False, "No account found for that email address."

    if password != ACCOUNTS[email]:
        return False, "Incorrect password. Please try again."

    return True, "Signed in."
